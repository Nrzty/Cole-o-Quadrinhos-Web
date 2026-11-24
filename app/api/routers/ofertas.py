from datetime import date
from collections import Counter
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routers.desejos import listar
from app.database import get_db
from app.services import leitura
from app.services.quadrinho_service import QuadrinhoService
from panini.compras import PASTA, configurar, recomendar
from panini.panini import BLACK_FRIDAY, baixar, endereco, extrair, filtros_campanha

router = APIRouter(prefix="/api", tags=["Ofertas Panini"])


class ConsultaOfertas(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


def ler_pagina(url):
    html, final = baixar(url)
    partes = urlsplit(final)
    if partes.path.rstrip("/") == "/black-friday-panini" and not partes.query:
        filtros = filtros_campanha(html, final)
        if filtros:
            return {"itens": [], "proxima": None, "editorias": filtros}
    avisos = []
    itens, proxima = extrair(html, final, avisos)
    return {"itens": itens, "proxima": proxima,
            "avisos": [f"{motivo} ({quantidade})" for motivo, quantidade in Counter(avisos).items()]}


def ler_campanha_filtrada(url):
    try:
        return ler_pagina(url)
    except ValueError:
        partes = urlsplit(url)
        query = parse_qs(partes.query)
        if (partes.path.rstrip("/") != "/black-friday-panini" or not query.get("editorial")
                or set(query) - {"editorial", "p"} or query.get("p", ["1"]) != ["1"]):
            raise
        # A campanha publica seu próprio endereço para cada filtro editorial.
        html, final = baixar(BLACK_FRIDAY)
        alternativa = filtros_campanha(html, final).get(query["editorial"][0])
        if not alternativa or alternativa == url or alternativa.rstrip("/") == BLACK_FRIDAY:
            raise
        return ler_pagina(alternativa)


@router.post("/ofertas")
def buscar_ofertas(consulta: ConsultaOfertas):
    try:
        url = endereco(consulta.url.strip())
    except ValueError as exc:
        raise HTTPException(422, "Informe uma URL HTTPS da Panini Brasil.") from exc
    try:
        return ler_campanha_filtrada(url)
    except HTTPError as exc:
        raise HTTPException(502, f"A Panini respondeu com HTTP {exc.code}.") from exc
    except OSError as exc:
        raise HTTPException(502, "Não foi possível acessar a Panini. Tente novamente.") from exc
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/ofertas/ranking")
def ranking_pagina(consulta: ConsultaOfertas, db=Depends(get_db)):
    pagina = buscar_ofertas(consulta)
    itens = pagina.pop("itens")
    unicos = {item["url"]: item for item in itens}
    ranking = []
    if unicos:
        resultado = recomendar(unicos.values(), leitura, QuadrinhoService(db).listar(limit=None),
                               listar(db), {}, date.today(), {}, configurar(PASTA / "config.toml"), None)
        ranking = resultado["ranking"]
    return {**pagina, "produtos": list(unicos), "ranking": ranking}
