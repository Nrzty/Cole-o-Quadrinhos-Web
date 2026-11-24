"""Coleta ofertas da Panini. Requer Python 3 e beautifulsoup4.
Uso: python panini.py [-o ofertas.csv] pesquisa a Batfamília. Uma URL explícita mantém o modo de categoria.
Para classificar a Black Friday por editorial, passe https://panini.com.br/black-friday-panini.
"""
import argparse
import csv
import json
import os
import re
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup

PADRAO = "https://panini.com.br/black-friday-panini?editorial=DC+Comics&p=1"
CAMPOS = ("titulo", "preco_atual", "preco_referencia", "economia", "desconto_pct",
          "disponibilidade", "url", "pagina", "coleta_utc")


def endereco(url):
    partes = urlsplit(url)
    if partes.scheme != "https" or not re.fullmatch(r"(?:www\.)?panini\.com\.br(?::443)?", partes.netloc, re.I):
        raise ValueError("Informe uma URL HTTPS da Panini Brasil.")
    return url


def preco(elemento):
    if elemento is None:
        return None
    valor = elemento.get("data-price-amount") or elemento.get("content")
    if valor and re.fullmatch(r"\d+(?:\.\d+)?", valor):
        return Decimal(valor)
    encontrado = re.search(r"R\$\s*([\d.]+,\d{2})", elemento.get_text(" ", strip=True))
    if encontrado:
        return Decimal(encontrado[1].replace(".", "").replace(",", "."))
    return None


def imagem_capa(bloco, url, ficha=False):
    seletor = ('meta[property="og:image"], .product.media img.gallery-placeholder__image, .product.media img[itemprop="image"]'
               if ficha else 'img.product-image-photo, .product-item-photo img, .product-image-wrapper img')
    for tag in bloco.select(seletor):
        for atributo in ("content", "data-original", "data-src", "src"):
            valor = tag.get(atributo)
            if not valor or valor.startswith("data:") or "/placeholder/" in valor.lower():
                continue
            imagem = urlsplit(urljoin(url, valor))
            if imagem.scheme in {"http", "https"} and imagem.hostname:
                return imagem._replace(scheme="https").geturl()
    return None


def extrair(html, url, avisos=None):
    soup = BeautifulSoup(html, "html.parser")
    produto = soup.select_one(".product-info-main")
    cards = [produto] if produto else soup.select(".products.list .product-item, .product-items .product-item, .products-grid .product-item")
    if not cards:
        vazia = soup.select_one(".message.empty")
        if vazia and re.search(r"nenhum produto|não encontramos|sem produtos", vazia.get_text(" ", strip=True), re.I):
            return [], None
        if soup.title:
            titulo = soup.title.get_text(" ", strip=True)[:100]
            raise ValueError(f'A Panini retornou a página “{titulo}”, sem cartões de produtos reconhecidos.')
        raise ValueError(f"Sem cartões de produtos reconhecidos em {url}")
    linhas = []
    horario = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for card in cards:
        link = soup.select_one("h1.page-title, h1") if produto else card.select_one("a.product-item-link, .product-item-name a[href]")
        if not link or (not produto and not link.get("href")):
            if avisos is not None and not produto:
                avisos.append("Produto sem link.")
                continue
            raise ValueError(f"Produto sem link em {url}")
        atual = preco(card.select_one('[data-price-type="finalPrice"], .special-price .price, .price-box .normal-price .price'))
        if atual is None:
            atual = preco(card.select_one(".price-box .price:not(.old-price .price), [itemprop=price]"))
        if atual is None:
            if avisos is not None and not produto:
                avisos.append("Produto sem preço legível.")
                continue
            raise ValueError(f"Preço ilegível: {link.get_text(strip=True)}")
        antigo = preco(card.select_one('[data-price-type="oldPrice"], .old-price .price'))
        economia = antigo - atual if antigo and antigo >= atual else None
        texto = card.get_text(" ", strip=True).lower()
        estoque = "não informado"
        if "avise-me" in texto or "fora de estoque" in texto:
            estoque = "indisponível"
        elif card.select_one('form[data-role="tocart-form"] button.tocart, button.tocart:not([disabled])') or any(b.get_text(strip=True).casefold() == "adicionar" for b in card.select("button:not([disabled])")):
            estoque = "compra disponível"
        linhas.append(dict(zip(CAMPOS, (link.get_text(" ", strip=True), atual, antigo, economia,
            (100 * economia / antigo).quantize(Decimal(".01")) if economia is not None else None,
            estoque, url if produto else endereco(urljoin(url, link["href"])), url, horario))))
        linhas[-1]["capa_url"] = imagem_capa(soup if produto else card, url, ficha=bool(produto))
    if produto:
        return linhas, None
    numero = int(parse_qs(urlsplit(url).query).get("p", ["1"])[0])
    paginas = [(int(p), a) for a in soup.select(".pages a[href], link[rel~=next][href]")
               for p in parse_qs(urlsplit(urljoin(url, a["href"])).query).get("p", []) if p.isdecimal()]
    proxima = next((a for p, a in paginas if p == numero + 1), None)
    ha_mais = any(p > numero for p, _ in paginas)
    faixa = soup.select_one(".toolbar-amount")
    if faixa:
        limites = re.search(r"(\d+)\s*[-–]\s*(\d+)\s+de\s+([\d.]+)", faixa.get_text(" ", strip=True))
        ha_mais = ha_mais or (limites and int(limites[2]) < int(limites[3].replace(".", "")))
    origem = urlsplit(url)
    filtros = parse_qs(origem.query)
    if not proxima and ha_mais:
        filtros["p"] = [str(numero + 1)]
        return linhas, origem._replace(query=urlencode(filtros, doseq=True), fragment="").geturl()
    if proxima:
        destino = urlsplit(endereco(urljoin(url, proxima["href"])))
        consulta = parse_qs(destino.query)
        for k, v in filtros.items():
            if k == "p" or consulta.get(k) == v:
                continue
            if k in consulta or destino.path.rstrip("/") != origem.path.rstrip("/"):
                if avisos is None:
                    raise ValueError("A próxima página mudou o filtro da consulta.")
                avisos.append("Paginação interrompida: a Panini mudou o filtro.")
                return linhas, None
            consulta[k] = v
        return linhas, destino._replace(query=urlencode(consulta, doseq=True), fragment="").geturl()
    return linhas, None



BASE = "https://panini.com.br"
NOMES = {
    "Batman": "batman|bruce wayne|cavaleiro das trevas|detective comics",
    "Robin": "robin|robins|menino prodigio",
    "Asa Noturna": "asa noturna|nightwing|dick grayson|ric grayson",
    "Capuz Vermelho": "capuz vermelho|red hood|jason todd",
    "Tim Drake": "tim drake|robin vermelho|red robin",
    "Damian Wayne": "damian wayne|filho do batman",
    "Batgirl": "batgirl|batgirls|barbara gordon|oraculo|oracle|cassandra cain|orphan|stephanie brown",
    "Batwoman": "batwoman|kate kane",
    "Batwing": "batwing|luke fox|david zavimbe",
    "Aliados": "alfred pennyworth|duke thomas|spoiler|azrael|jean paul valley|helena bertinelli|huntress|cacadora|harper row|bluebird|batmóvel|batfamilia|bat family",
    "Equipes": "aves de rapina|birds of prey|batman incorporated|batman s a",
}


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def identificar(texto):
    texto = " " + normalizar(texto) + " "
    texto = texto.replace(" robin hood ", " ").replace(" nico robin ", " ")
    return [nome for nome, termos in NOMES.items()
            if any(" " + normalizar(t) + " " in texto for t in termos.split("|"))]


class RedirecionamentoPanini(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, endereco(newurl))


def baixar(url):
    time.sleep(0.8)
    opener = build_opener(RedirecionamentoPanini())
    with opener.open(Request(endereco(url), headers={"User-Agent": "PaniniOfertaReader/2.0"}), timeout=30) as res:
        final = endereco(res.geturl())
        consulta = parse_qs(urlsplit(final).query)
        if any(consulta.get(k) != v for k, v in parse_qs(urlsplit(url).query).items() if k != "p"):
            raise ValueError("Filtro perdido no redirecionamento")
        return res.read(), final


def varrer(inicios, tematico):
    produtos, erros = {}, []
    for origem in inicios:
        url, vistas, produtos_locais = origem, set(), set()
        try:
            while url:
                html, final = baixar(url)
                linhas, seguinte = extrair(html, final)
                if final in vistas or all(r["url"] in produtos_locais for r in linhas):
                    raise ValueError("Página repetida")
                for r in linhas:
                    produtos_locais.add(r["url"])
                    anterior = produtos.get(r["url"])
                    if anterior:
                        anterior["fontes"].add(origem)
                        continue
                    r["fontes"] = {origem}
                    produtos[r["url"]] = r
                vistas.add(final)
                url = seguinte
        except (OSError, ValueError) as exc:
            erros.append(f"{url}: {exc}")
        print(f"{origem}: {len(vistas)} páginas lidas, {len(produtos_locais)} produtos", flush=True)
    resultado = []
    for r in produtos.values():
        if tematico:
            if not r["economia"] or r["economia"] <= 0:
                continue
            nomes = identificar(r["titulo"])
            evidencia = "título"
            if not nomes:
                try:
                    html, _ = baixar(r["url"])
                    ficha = BeautifulSoup(html, "html.parser")
                    descricao = ficha.select(".product.attribute.description, .product.attribute.overview, #description, #product-attribute-specs-table")
                    if not descricao:
                        raise ValueError("Descrição e detalhes ausentes")
                    nomes = identificar(" ".join(d.get_text(" ", strip=True) for d in descricao))
                    evidencia = "sinopse ou detalhes"
                except (OSError, ValueError) as exc:
                    erros.append(f'{r["url"]}: {exc}')
            if not nomes:
                continue
            r.update(personagens=", ".join(nomes), evidencia=evidencia)
        r["fontes"] = " | ".join(sorted(r["fontes"]))
        resultado.append(r)
    resultado.sort(key=lambda r: (r["disponibilidade"] != "compra disponível",
        r.get("evidencia") == "sinopse ou detalhes", -(r["desconto_pct"] or 0), r["preco_atual"]))
    return resultado, erros


def fontes_padrao():
    fontes = [PADRAO, BASE + "/dc-comics", BASE + "/desconto-saldao"]
    for termo in ("Batgirls", "Asa Noturna", "Capuz Vermelho", "Robin", "Batwoman", "Aves de Rapina"):
        fontes.append(BASE + "/catalogsearch/result/?" + urlencode({"q": termo}))
    return fontes


BLACK_FRIDAY = BASE + "/black-friday-panini"
EDITORIAS = {"Planet Manga": "Mangás", "Marvel Comics": "Marvel", "DC Comics": "DC"}


def filtros_campanha(html, final):
    sopa = BeautifulSoup(html, "html.parser")
    for script in sopa.select('script[type="text/x-magento-init"]'):
        conteudo = script.string or ""
        if "editorialFilter" in conteudo:
            config = json.loads(conteudo)
            componentes = config.get("*", {}).get("Magento_Ui/js/core/app", {}).get("components", {})
            itens = componentes.get("editorialFilter", {}).get("items", [])
            if itens:
                return {i["label"]: endereco(urljoin(final, i["url"])) for i in itens if i.get("label") in EDITORIAS and i.get("url")}
    return {}


def black_friday():
    resultado, erros = [], []
    try:
        html, final = baixar(BLACK_FRIDAY)
        filtros = filtros_campanha(html, final)
    except (OSError, ValueError, KeyError) as exc:
        return [], [f"{BLACK_FRIDAY}: {exc}"]
    for editorial, categoria in EDITORIAS.items():
        if editorial not in filtros:
            erros.append(f"Filtro ausente na campanha: {editorial}")
            continue
        origem = urljoin(final, filtros[editorial])
        linhas, falhas = varrer([origem], False)
        erros.extend(falhas)
        ofertas = [r for r in linhas if r["economia"] and r["economia"] > 0
                   and r["disponibilidade"] == "compra disponível"]
        ofertas.sort(key=lambda r: (-r["desconto_pct"], -r["economia"], r["preco_atual"], r["titulo"]))
        for r in ofertas:
            r["categoria"] = categoria
        resultado.extend(ofertas)
        print(f"\n{categoria} — {len(ofertas)} ofertas encontradas")
        for r in ofertas[:5]:
            print(f'{r["desconto_pct"]}% | R$ {r["preco_atual"]:.2f} | {r["titulo"]} | {r["url"]}')
    return resultado, erros


def salvar_excel(linhas, destino, campanha):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    livro = Workbook()
    livro.remove(livro.active)
    for categoria in EDITORIAS.values() if campanha else ["Ofertas"]:
        aba = livro.create_sheet(categoria)
        aba.freeze_panes = "A2"
        aba.sheet_view.showGridLines = False
        aba.append(["Título", "Preço da oferta", "Desconto", "Economia", "Preço original", "Loja"])
        aba.row_dimensions[1].height = 26
        for celula in aba[1]:
            celula.fill = PatternFill("solid", fgColor="17354D")
            celula.font = Font(bold=True, color="FFFFFF")
        for indice, largura in enumerate([84, 19, 16, 18, 19, 18], 1):
            aba.column_dimensions[get_column_letter(indice)].width = largura
        for r in linhas:
            if campanha and r["categoria"] != categoria:
                continue
            desconto = r["desconto_pct"]
            aba.append([r["titulo"], r["preco_atual"], desconto / 100 if desconto is not None else None,
                        r["economia"], r["preco_referencia"], "Ver na Panini"])
            titulo, atual, percentual, economia, original, link = aba[aba.max_row]
            titulo.data_type = "s"
            for celula in (atual, economia, original):
                celula.number_format = '"R$" #,##0.00'
            percentual.number_format = "0.00%"
            percentual.font = Font(bold=True, color="007055")
            link.hyperlink = r["url"]
            link.style = "Hyperlink"
            if titulo.row % 2:
                for celula in (titulo, atual, percentual, economia, original, link):
                    celula.fill = PatternFill("solid", fgColor="EFF5F7")
        aba.auto_filter.ref = aba.dimensions
    livro.save(destino)


def salvar(linhas, destino, campanha=False):
    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as arquivo:
        temporario = Path(arquivo.name)
    try:
        if destino.suffix.lower() == ".xlsx":
            salvar_excel(linhas, temporario, campanha)
            os.replace(temporario, destino)
            return
        with temporario.open("w", encoding="utf-8-sig", newline="") as arquivo:
            campos = (*CAMPOS, "fontes", "personagens", "evidencia", "capa_url")
            writer = csv.DictWriter(arquivo, ("categoria", *campos) if campanha else campos, delimiter=";")
            writer.writeheader()
            for linha in linhas:
                registro = dict(linha)
                for campo, valor in registro.items():
                    if isinstance(valor, Decimal):
                        registro[campo] = format(valor, "f").replace(".", ",")
                if registro["titulo"].lstrip().startswith(("=", "+", "-", "@")):
                    registro["titulo"] = "'" + registro["titulo"]
                writer.writerow(registro)
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("-o", type=Path, default=Path("ofertas.csv"))
    args = parser.parse_args()
    campanha = bool(args.url and args.url.rstrip("/") == BLACK_FRIDAY)
    if campanha:
        ofertas, erros = black_friday()
    else:
        ofertas, erros = varrer([endereco(args.url)] if args.url else fontes_padrao(), not args.url)
    if erros:
        for erro in erros:
            print("Falha:", erro)
        if ofertas:
            parcial = args.o.with_name(args.o.stem + ".parcial" + args.o.suffix)
            salvar(ofertas, parcial, campanha)
            print("Resultado parcial:", parcial)
        raise SystemExit(2)
    salvar(ofertas, args.o, campanha)
    print(f"{len(ofertas)} produtos salvos em {args.o}")

