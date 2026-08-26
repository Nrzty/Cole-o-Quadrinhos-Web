import httpx
from fastapi import HTTPException

class BrasilAPIService:
    BASE_URL = "https://brasilapi.com.br/api/isbn/v1"

    @classmethod
    async def fetch_isbn(cls, isbn: str) -> dict:
        """Busca informações de um ISBN na Brasil API."""
        isbn_limpo = isbn.replace("-", "").strip()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{cls.BASE_URL}/{isbn_limpo}")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise HTTPException(status_code=404, detail="ISBN não encontrado na Brasil API.")
                raise HTTPException(status_code=500, detail="Erro ao consultar a Brasil API.")
            except Exception:
                raise HTTPException(status_code=500, detail="Erro de conexão com a Brasil API.")
