from datetime import date
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.routers.desejos import listar
from app.database import get_db
from app.services import leitura
from app.services.quadrinho_service import QuadrinhoService
from panini.compras import PASTA, configurar, recomendar
from panini.panini import baixar, endereco, extrair, filtros_campanha

router = APIRouter(prefix="/api", tags=["Ofertas Panini"])


class ConsultaOfertas(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


@router.post("/ofertas")
def buscar_ofertas(consulta: ConsultaOfertas):
    try:
        url = endereco(consulta.url.strip())
    except ValueError as exc:
        raise HTTPException(422, "Informe uma URL HTTPS da Panini Brasil.") from exc
    try:
        html, final = baixar(url)
        partes = urlsplit(final)
        if partes.path.rstrip("/") == "/black-friday-panini" and not partes.query:
            filtros = filtros_campanha(html, final)
            if filtros:
                return {"itens": [], "proxima": None, "editorias": filtros}
        itens, proxima = extrair(html, final)
    except OSError as exc:
        raise HTTPException(502, "Não foi possível acessar a Panini. Tente novamente.") from exc
    except ValueError as exc:
        raise HTTPException(502, "Não foi possível ler os produtos dessa página da Panini.") from exc
    return {"itens": itens, "proxima": proxima}


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
