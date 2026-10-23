from pydantic import BaseModel, field_validator
from typing import Optional
import re

class QuadrinhoCreate(BaseModel):
    isbn: str
    tipo: str = 'Quadrinho'

    @field_validator('isbn')
    @classmethod
    def limpar_isbn(cls, valor):
        valor = re.sub(r'[\s-]', '', valor).upper()
        if not re.fullmatch(r'(?:[0-9]{13}|[0-9]{9}[0-9X])', valor):
            raise ValueError('Informe um ISBN de 10 ou 13 caracteres.')
        return valor

class QuadrinhoManualCreate(BaseModel):
    isbn: Optional[str] = None
    titulo: str
    autor: Optional[str] = None
    editora: Optional[str] = None
    ano: Optional[int] = None
    tipo: str = 'Quadrinho'
    capa_url: Optional[str] = None
    colecao: Optional[str] = None

    @field_validator('ano', mode='before')
    @classmethod
    def ano_vazio(cls, valor):
        return None if valor == '' else valor

    @field_validator('isbn', mode='before')
    @classmethod
    def isbn_opcional(cls, valor):
        if not valor or not valor.strip():
            return None
        return QuadrinhoCreate.limpar_isbn(valor)

    @field_validator('titulo')
    @classmethod
    def titulo_obrigatorio(cls, valor):
        if not valor.strip():
            raise ValueError('O título é obrigatório.')
        return valor.strip()

    @field_validator('capa_url')
    @classmethod
    def validar_capa(cls, valor):
        if valor and not valor.startswith(('https://', 'http://')):
            raise ValueError('A capa deve ser um link HTTP ou HTTPS.')
        return valor or None

class QuadrinhoResponse(BaseModel):
    id: int
    isbn: Optional[str] = None
    titulo: str
    autor: Optional[str] = None
    editora: Optional[str] = None
    ano: Optional[int] = None
    tipo: str
    capa_url: Optional[str] = None
    colecao: str = 'Outras coleções'
    colecao_manual: bool = False
    model_config = {'from_attributes': True}
