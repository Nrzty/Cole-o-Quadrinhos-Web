from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import QuadrinhoCreate, QuadrinhoManualCreate, QuadrinhoResponse
from app.services.quadrinho_service import QuadrinhoService
from app.services.capas import buscar_capa

router = APIRouter(prefix='/api/quadrinhos', tags=['Quadrinhos'])

@router.post('/', response_model=QuadrinhoResponse)
async def adicionar(dados: QuadrinhoCreate, db: Session = Depends(get_db)):
    return await QuadrinhoService(db).adicionar(dados)

@router.post('/manual', response_model=QuadrinhoResponse)
async def manual(dados: QuadrinhoManualCreate, db: Session = Depends(get_db)):
    return await QuadrinhoService(db).adicionar_manual(dados)

@router.get('/', response_model=list[QuadrinhoResponse])
def listar(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return QuadrinhoService(db).listar(skip, limit)

class CapaUpdate(BaseModel):
    capa_url: str
    validar = field_validator('capa_url')(QuadrinhoManualCreate.validar_capa.__func__)

class ColecaoUpdate(BaseModel):
    colecao: str | None = None

@router.post('/{id}/buscar-capa', response_model=QuadrinhoResponse)
async def completar_capa(id: int, db: Session = Depends(get_db)):
    service = QuadrinhoService(db)
    q = service.obter(id)
    if not q.capa_url:
        url = await buscar_capa(q.isbn)
        if url:
            q.capa_url = url
            return service.salvar(q)
    return service.resposta(q)

@router.patch('/{id}/colecao', response_model=QuadrinhoResponse)
def colecao(id: int, dados: ColecaoUpdate, db: Session = Depends(get_db)):
    service = QuadrinhoService(db)
    q = service.obter(id)
    q.colecao = (dados.colecao or '').strip() or None
    return service.salvar(q)

@router.patch('/{id}/capa', response_model=QuadrinhoResponse)
def capa(id: int, dados: CapaUpdate, db: Session = Depends(get_db)):
    service = QuadrinhoService(db)
    q = service.obter(id)
    q.capa_url = dados.capa_url or None
    return service.salvar(q)

@router.delete('/{id}')
def remover(id: int, db: Session = Depends(get_db)):
    QuadrinhoService(db).remover(id)
    return {'mensagem': 'Quadrinho removido.'}
