from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from panini.panini import baixar, endereco, extrair

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
        itens, proxima = extrair(html, final)
    except OSError as exc:
        raise HTTPException(502, "Não foi possível acessar a Panini. Tente novamente.") from exc
    except ValueError as exc:
        raise HTTPException(502, "Não foi possível ler os produtos dessa página da Panini.") from exc
    return {"itens": itens, "proxima": proxima}
