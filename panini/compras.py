"""Ordena ofertas da Panini usando a coleção do Quadrinhos (Python 3.11+)."""
import argparse
import csv
import json
import math
import re
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from panini import identificar, normalizar

try:
    from rapidfuzz.fuzz import ratio
    MOTOR_FUZZY = "RapidFuzz"
except ImportError:
    MOTOR_FUZZY = "Indel normalizado (Python)"

    def ratio(a, b):
        """Mesma métrica de fuzz.ratio: 2 × LCS / soma dos comprimentos."""
        masks = {}
        for i, char in enumerate(b):
            masks[char] = masks.get(char, 0) | (1 << i)
        bits = 0
        for char in a:
            x = masks.get(char, 0) | bits
            bits = x & ~(x - ((bits << 1) | 1))
        return 200 * bits.bit_count() / (len(a) + len(b)) if a or b else 100


PASTA = Path(__file__).resolve().parent
FORMATOS = r"\b(?:capa dura|capa mole|encadernado|mensal|omnibus|brochura|edicao absoluta|dc de bolso|dc compact|edicao de luxo)\b"
NUMERO = re.compile(r"\b(?:vol(?:ume)?|parte|livro|numero|n|edicao)\s*(\d+)\b")


def dinheiro(valor):
    s = str(valor).strip().removeprefix("R$").strip()
    quantia = Decimal(s.replace(".", "").replace(",", ".") if "," in s else s)
    if not quantia.is_finite() or quantia < 0:
        raise ValueError(f"Valor inválido: {valor}")
    return quantia


def ofertas_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        if not {"titulo", "url", "preco_atual"} <= set(leitor.fieldnames or []):
            raise ValueError(f"{path}: faltam titulo, url ou preco_atual")
        for i, row in enumerate(leitor, 2):
            try:
                for k in ("preco_atual", "preco_referencia", "economia", "desconto_pct"):
                    row[k] = dinheiro(row[k]) if row.get(k) else None
                if not row["titulo"].strip() or not row["url"].strip() or row["preco_atual"] is None:
                    raise ValueError("produto incompleto")
                if row["preco_atual"] != row["preco_atual"].quantize(Decimal(".01")):
                    raise ValueError("preço fracionário em centavos")
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"{path}, linha {i}: {exc}") from exc
            yield row


def carregar_estante(pasta):
    sys.path.insert(0, str(pasta.resolve()))
    from app.database import SessionLocal
    from app.api.routers.desejos import listar
    from app.services import leitura
    from app.services.quadrinho_service import QuadrinhoService

    with SessionLocal() as db:
        acervo = QuadrinhoService(db).listar(limit=None)
        desejos = listar(db)
    return leitura, acervo, desejos


def entidade(row, leitura):
    titulo = row["titulo"].strip()
    texto = normalizar(titulo)
    formato = re.search(FORMATOS, texto + " " + normalizar(row.get("tipo") or ""))
    base = re.sub(FORMATOS, " ", texto)
    base = " ".join(re.sub(r"\b(?:reimpressao|nova edicao|capa variante)\b", "", base).split())
    split = re.split(r"\s*:\s*|\s+[-–—]\s+", titulo, maxsplit=1)
    par = leitura.serie_volume(row)
    fase = re.search(r"\b(?:fase|temporada|etapa)\b", base)
    if fase and par and fase[0] not in normalizar(par[0]):
        par = None
    marcador = NUMERO.search(base)
    if not par and not fase:
        if marcador and base[:marcador.start()].strip():
            par = (base[:marcador.start()].strip(), int(marcador[1]))
        else:
            final = re.fullmatch(r"(.+?)\s+(\d{1,3})", base) if not re.search(r"\b(?:ano|terra|universo|gotham) \d+$", base) else None
            if final:
                par = (final[1], int(final[2]))
    serie = normalizar(par[0]) if par else normalizar(split[0])
    volume = par[1] if par else None
    autores = re.split(r"[,;|]", row.get("autor") or "")
    personagens = set(identificar(titulo))
    personagens.update(x.strip() for x in (row.get("personagens") or "").split(",") if x.strip())
    historias = leitura.historias(row)
    # "Ano Um" também é subtítulo de histórias independentes de outros heróis.
    if not re.fullmatch(r"(?:batman )?(?:ano um|year one)(?: (?:vol|volume|parte) \d+)?", base):
        historias = {(k, n) for k, n in historias if k != "ano-um"}
    arcos = {k for k, _ in historias if not k.startswith("titulo:")}
    subtitulo = split[1] if len(split) > 1 else ""
    era = re.search(r"\b(?:novos 52|renascimento|era de (?:ouro|prata|bronze)|nova dc|fase \d+|temporada \d+)\b", texto)
    selo = re.search(r"\b(?:dc comics|marvel comics|planet manga|panini comics)\b", texto)
    return dict(titulo=titulo, chave=base or texto, serie=serie, volume=volume,
                subtitulo=subtitulo, formato=normalizar(row.get("formato") or (formato[0] if formato else "")),
                editora=row.get("editora") or (selo[0] if selo else ""), linha=row.get("colecao") or row.get("categoria") or "",
                personagens=sorted({normalizar(x) for x in personagens}), autor=sorted({normalizar(x) for x in autores if x.strip()}),
                arco=sorted(arcos), era=normalizar(row.get("era") or (era[0] if era else "")),
                historias=historias)


def comparar(a, b):
    if a["volume"] != b["volume"]:
        return 0, ""
    if a["chave"] == b["chave"]:
        return 1, "título normalizado"
    if a["volume"] is not None and a["serie"] == b["serie"]:
        if not (a["subtitulo"] and b["subtitulo"] and normalizar(a["subtitulo"]) != normalizar(b["subtitulo"])):
            return 1, "mesma série e número"
    if a["arco"] and a["historias"] == b["historias"] and (a["serie"] == b["serie"] or
            a["chave"] in b["chave"] or b["chave"] in a["chave"]):
        return 1, "mesma história identificada na biblioteca"
    if re.findall(r"\d+", a["chave"]) != re.findall(r"\d+", b["chave"]):
        return 0, ""
    return ratio(a["chave"], b["chave"]) / 100, "similaridade textual"


def melhor(alvo, entidades):
    return max(((conf, motivo, item["titulo"]) for item in entidades
                for conf, motivo in [comparar(alvo, item)]), default=(0, "", ""))


def valores(ent, campo):
    v = ent[campo]
    return v if isinstance(v, list) else [v] if v else []


def perfil(acervo, entidades, compras, hoje, cfg):
    contagens = {k: Counter() for k in cfg["perfil"]}
    soma = total = 0
    for row, ent in zip(acervo, entidades):
        compra = compras.get(str(row["id"]), {})
        peso = 1
        if compra.get("data"):
            idade = (hoje - date.fromisoformat(compra["data"])).days
            if idade < 0:
                raise ValueError(f"Aquisição futura para id {row['id']}")
            peso = 2 ** (-idade / cfg["regras"]["meia_vida_dias"])
        if compra.get("preco_pago") is not None:
            soma += peso * float(dinheiro(compra["preco_pago"]))
            total += peso
        for campo, contador in contagens.items():
            for valor in valores(ent, campo):
                contador[valor] += peso
    return contagens, soma / total if total else None


def pontuar(row, ent, contagens, media, volumes, desejo, historico, cfg):
    r = cfg["regras"]
    numero = ent["volume"]
    nums = volumes.get(ent["serie"], set())
    lacuna = bool(nums and numero is not None and min(nums) < numero < max(nums) and numero not in nums)
    proximo = bool(nums and numero == max(nums) + 1)
    sinais = {}
    for campo, freq in contagens.items():
        if freq:
            sinais[campo] = max((freq[v] for v in valores(ent, campo)), default=0) / max(freq.values())
    pesos = cfg["perfil"]
    afin = sum(pesos[k] * v for k, v in sinais.items()) / (sum(pesos[k] for k in sinais) or 1)
    categoria = ("WISHLIST" if desejo else "LACUNA" if lacuna else "CONTINUACAO" if proximo
                 else "AFINIDADE" if afin >= r["afinidade"] else "DESCOBERTA")
    preco = row["preco_atual"]
    economia, pct = row["economia"], row["desconto_pct"]
    if economia is None and row["preco_referencia"]:
        economia = max(0, row["preco_referencia"] - preco)
    if pct is None and economia is not None and row["preco_referencia"]:
        pct = 100 * economia / row["preco_referencia"]
    mix = r["fracao_desconto_percentual"]
    estoque = normalizar(row.get("disponibilidade") or "")
    disponivel = {"compra disponivel": 1, "disponivel": 1, "pre venda": r["pre_venda"],
                  "indisponivel": 0}.get(estoque, r["estoque_desconhecido"])
    minimo = historico.get(row["url"])
    unidades = row.get("unidades")
    componentes = dict(continuidade=1 if lacuna else r["continuacao"] if proximo else 0,
        wishlist=int(desejo), afinidade=afin, desconto=mix * min(1, float(pct or 0)/100)
        + (1-mix) * min(1, float(economia or 0)/r["economia_plena_reais"]),
        preco_relativo=None if media is None else min(1, media / float(preco)) if preco else 1,
        disponibilidade=disponivel, urgencia=None if unidades in (None, "") else int(0 < int(unidades) <= r["estoque_baixo"]),
        historico=None if minimo is None else int(preco <= minimo))
    detalhe = {k: dict(valor=v, peso=p, pontos=round((v or 0)*p, 4))
               for k, p in cfg["pesos"].items() for v in [componentes[k]]}
    return dict(categoria=categoria, score=round(sum(x["pontos"] for x in detalhe.values()), 4),
                componentes=detalhe, afinidade_por_campo=sinais, volumes_possuidos=sorted(nums),
                minimo_anterior=minimo, economia=economia, desconto_pct=pct)


def recomendar(ofertas, leitura, acervo, desejos, compras, hoje, historico, cfg, orcamento):
    possuidos = [entidade(q, leitura) for q in acervo]
    procurados = [entidade(q, leitura) for q in desejos]
    contagens, media = perfil(acervo, possuidos, compras, hoje, cfg)
    volumes = defaultdict(set)
    for item in possuidos:
        if item["volume"] is not None:
            volumes[item["serie"]].add(item["volume"])
    ranking, revisar, descartes = [], [], Counter()
    regras = cfg["regras"]
    por_url = {}
    for row in ofertas:
        anterior = por_url.get(row["url"])
        if anterior and anterior != row:
            raise ValueError(f"Ofertas divergentes para {row['url']}")
        por_url[row["url"]] = row
    for row in por_url.values():
        ent = entidade(row, leitura)
        # Os cartões frequentemente creditam o roteirista apenas no título.
        titulo = " " + normalizar(row["titulo"]) + " "
        ent["autor"] = sorted(set(ent["autor"]) | {nome for nome in contagens["autor"]
                                                  if " " + nome + " " in titulo})
        proprio = melhor(ent, possuidos)
        desejo = melhor(ent, procurados)
        if proprio[0] >= regras["match"]:
            descartes["JA_POSSUO"] += 1
            continue
        if normalizar(row.get("disponibilidade") or "") in {"indisponivel", "fora de estoque"} or str(row.get("unidades")) == "0":
            descartes["INDISPONIVEL"] += 1
            continue
        confirmado = desejo[0] >= regras["match"]
        conf, metodo, correspondente = max(proprio, desejo)
        campos = {k: v for k, v in ent.items() if k not in {"historias", "chave"}}
        item = dict(**campos, preco=row["preco_atual"], url=row["url"],
                    disponibilidade=row.get("disponibilidade") or "não informada",
                    coleta_utc=row.get("coleta_utc") or None,
                    match_confidence=round(conf, 6), metodo=metodo or None,
                    correspondente=correspondente if conf else None)
        sobreposicao = next((q["titulo"] for q in possuidos
                             if set(ent["arco"]) & set(q["arco"]) and
                             (ent["volume"] is None or q["volume"] is None or ent["volume"] == q["volume"])), None)
        if sobreposicao or proprio[0] >= regras["revisao"] or (not confirmado and desejo[0] >= regras["revisao"]):
            item["motivo_revisao"] = ("sobreposição de conteúdo com " + sobreposicao if sobreposicao
                                      else "possível correspondência na estante" if proprio[0] >= regras["revisao"]
                                      else "possível correspondência nos desejos")
            item["candidato_revisao"] = sobreposicao or (proprio[2] if proprio[0] >= regras["revisao"] else desejo[2])
            revisar.append(item)
            continue
        item.update(pontuar(row, ent, contagens, media, volumes, confirmado, historico, cfg))
        if item["categoria"] == "DESCOBERTA" and item["score"] < regras["descoberta_minima"]:
            descartes["DESCOBERTA_ABAIXO_DO_MINIMO"] += 1
            continue
        ranking.append(item)
    ranking.sort(key=lambda x: (-x["score"], x["preco"], x["titulo"], x["url"]))
    relatorio = dict(data_referencia=hoje, motor_fuzzy=MOTOR_FUZZY, ofertas_unicas=len(por_url),
                     colecao=len(acervo), desejos=len(desejos), perfil=contagens, media_paga=media,
                     ranking=ranking, revisar=sorted(revisar, key=lambda x: x["url"]), descartes=descartes)
    if orcamento is not None:
        saldo = orcamento
        cesta, escolhidos = [], []
        for item in ranking:
            if item["preco"] > saldo:
                continue
            ent = entidade(por_url[item["url"]], leitura)
            if any(comparar(ent, outro)[0] >= regras["revisao"] or
                   (ent["historias"] & outro["historias"] and ent["volume"] == outro["volume"])
                   for outro in escolhidos):
                continue
            cesta.append(dict(titulo=item["titulo"], preco=item["preco"], url=item["url"]))
            escolhidos.append(ent)
            saldo -= item["preco"]
        relatorio.update(orcamento=orcamento, cesta=cesta, total=orcamento-saldo, saldo=saldo)
    return relatorio


def configurar(path):
    with path.open("rb") as arquivo:
        cfg = tomllib.load(arquivo)
    pesos, regras = cfg["pesos"], cfg["regras"]
    if set(pesos) != set("continuidade wishlist afinidade desconto preco_relativo disponibilidade urgencia historico".split()):
        raise ValueError("Confira os oito nomes de componentes em [pesos]")
    if any(p < 0 for p in pesos.values()) or not math.isclose(sum(pesos.values()), 100):
        raise ValueError("Os pesos devem ser positivos ou zero e somar 100")
    if not 0 < regras["revisao"] <= regras["match"] <= 1:
        raise ValueError("É necessário 0 < revisao <= match <= 1")
    for k in ("afinidade", "fracao_desconto_percentual", "continuacao", "pre_venda", "estoque_desconhecido"):
        if not 0 <= regras[k] <= 1:
            raise ValueError(f"{k} precisa estar entre 0 e 1")
    if not 0 <= regras["descoberta_minima"] <= 100 or min(regras["economia_plena_reais"], regras["meia_vida_dias"]) <= 0:
        raise ValueError("Limiares de descoberta, economia ou meia-vida inválidos")
    if set(cfg["perfil"]) != set("serie personagens autor arco era formato".split()) or min(cfg["perfil"].values()) < 0 or sum(cfg["perfil"].values()) <= 0:
        raise ValueError("Confira os pesos do perfil")
    return cfg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ofertas", type=Path, help="CSV produzido por panini.py")
    parser.add_argument("--biblioteca", type=Path, default=PASTA.parent)
    parser.add_argument("--config", type=Path, default=PASTA / "config.toml")
    parser.add_argument("--orcamento", type=dinheiro)
    parser.add_argument("--historico", type=Path, action="append", default=[], help="CSV de uma coleta anterior")
    parser.add_argument("--compras", type=Path, help="JSON por id da biblioteca com data e/ou preco_pago")
    parser.add_argument("--data", type=date.fromisoformat, default=date.today())
    parser.add_argument("-o", "--saida", type=Path, help="arquivo JSON (padrão: saída padrão)")
    args = parser.parse_args()
    entradas = [args.ofertas, args.config, *args.historico] + ([args.compras] if args.compras else [])
    if args.saida and args.saida.resolve() in {p.resolve() for p in entradas}:
        parser.error("A saída deve ser diferente dos arquivos de entrada")
    try:
        cfg = configurar(args.config)
        leitura, acervo, desejos = carregar_estante(args.biblioteca)
        compras = json.loads(args.compras.read_text(encoding="utf-8-sig")) if args.compras else {}
        historico = {}
        for path in args.historico:
            if path.resolve() == args.ofertas.resolve():
                raise ValueError("Use somente coletas anteriores em --historico")
            for row in ofertas_csv(path):
                url, preco = row["url"], row["preco_atual"]
                historico[url] = min(preco, historico.get(url, preco))
        resultado = recomendar(ofertas_csv(args.ofertas), leitura, acervo, desejos, compras,
                               args.data, historico, cfg, args.orcamento)
        resultado["arquivo_ofertas"] = str(args.ofertas)
        saida = json.dumps(resultado, ensure_ascii=False, default=str, indent=2)
        if args.saida:
            args.saida.write_text(saida + "\n", encoding="utf-8")
        else:
            print(saida)
    except (ValueError, InvalidOperation, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
