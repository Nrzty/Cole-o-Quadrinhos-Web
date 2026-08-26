from pydantic import BaseModel
from typing import Optional

class QuadrinhoCreate(BaseModel):
    isbn: str
    tipo: str = "Quadrinho"

class QuadrinhoManualCreate(BaseModel):
    isbn: Optional[str] = None
    titulo: str
    autor: Optional[str] = None
    editora: Optional[str] = None
    ano: Optional[int] = None
    tipo: str = "Quadrinho"
    capa_url: Optional[str] = None

class QuadrinhoResponse(BaseModel):
    id: int
    isbn: str
    titulo: str
    autor: Optional[str] = None
    editora: Optional[str] = None
    ano: Optional[int] = None
    tipo: str
    capa_url: Optional[str] = None

    model_config = {"from_attributes": True}
