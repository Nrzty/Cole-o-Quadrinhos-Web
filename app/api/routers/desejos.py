from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Desejo, Quadrinho
from app.schemas import QuadrinhoManualCreate
from app.services.quadrinho_service import QuadrinhoService
from app.services.recomendacoes import recomendar, chave_isbn, chave_titulo

router = APIRouter(prefix='/api', tags=['Aquisições futuras'])

class DesejoCreate(QuadrinhoManualCreate):
    prioridade: int = Field(2, ge=1, le=3)
    notas: str = Field('', max_length=2000)

class DesejoUpdate(QuadrinhoManualCreate):
    prioridade: int = Field(2, ge=1, le=3)
    notas: str = Field('', max_length=2000)

def resposta(q):
    return {c.name: getattr(q, c.name) for c in q.__table__.columns}

def verificar(db, dados, ignorar=None):
    for tabela in (Quadrinho, Desejo):
        for q in db.query(tabela).all():
            if tabela is Desejo and q.id == ignorar:
                continue
            if (dados.isbn and chave_isbn(dados.isbn) == chave_isbn(q.isbn)) or chave_titulo(dados.titulo) == chave_titulo(q.titulo):
                raise HTTPException(409, 'Esta edição já está na estante ou na lista de desejos.')

@router.get('/desejos')
def listar(db: Session = Depends(get_db)):
    return [resposta(q) for q in db.query(Desejo).order_by(Desejo.prioridade, Desejo.id.desc()).all()]

@router.post('/desejos')
def adicionar(dados: DesejoCreate, db: Session = Depends(get_db)):
    verificar(db, dados)
    q = Desejo(**dados.model_dump())
    db.add(q)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'ISBN já está na lista de desejos.')
    db.refresh(q)
    return resposta(q)

@router.put('/desejos/{id}')
def editar(id: int, dados: DesejoUpdate, db: Session = Depends(get_db)):
    q = db.get(Desejo, id)
    if not q:
        raise HTTPException(404, 'Desejo não encontrado.')
    verificar(db, dados, id)
    for nome, valor in dados.model_dump().items():
        setattr(q, nome, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'ISBN já está na lista de desejos.')
    db.refresh(q)
    return resposta(q)

@router.delete('/desejos/{id}')
def remover(id: int, db: Session = Depends(get_db)):
    q = db.get(Desejo, id)
    if not q:
        raise HTTPException(404, 'Desejo não encontrado.')
    db.delete(q)
    db.commit()
    return {'mensagem': 'Desejo removido.'}

@router.post('/desejos/{id}/adquirir')
def adquirir(id: int, db: Session = Depends(get_db)):
    q = db.get(Desejo, id)
    if not q:
        raise HTTPException(404, 'Desejo não encontrado.')
    dados = {nome: getattr(q, nome) for nome in QuadrinhoManualCreate.model_fields}
    # A edição já pode ter sido cadastrada diretamente na estante.
    existente = next((x for x in db.query(Quadrinho).all() if (q.isbn and chave_isbn(x.isbn) == chave_isbn(q.isbn)) or chave_titulo(x.titulo) == chave_titulo(q.titulo)), None)
    if existente:
        db.delete(q)
        db.commit()
        return QuadrinhoService(db).resposta(existente)
    novo = Quadrinho(**dados)
    db.add(novo)
    db.delete(q)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'A edição já está na estante. Atualize a página.')
    db.refresh(novo)
    return QuadrinhoService(db).resposta(novo)

@router.get('/recomendacoes')
async def recomendacoes(db: Session = Depends(get_db)):
    service = QuadrinhoService(db)
    acervo = [service.resposta(q) for q in db.query(Quadrinho).all()]
    desejos = [resposta(q) for q in db.query(Desejo).all()]
    return await recomendar(acervo, desejos)


from typing import Literal
from pydantic import BaseModel

class ConsultaRecomendacoes(BaseModel):
    modo: Literal['para_voce', 'continuar', 'explorar'] = 'para_voce'
    rodada: int = Field(0, ge=0, le=20)
    vistos: list[str] = Field(default_factory=list, max_length=200)
    atualizar: bool = False

@router.post('/recomendacoes/consulta')
async def consultar_recomendacoes(dados: ConsultaRecomendacoes, db: Session = Depends(get_db)):
    service = QuadrinhoService(db)
    acervo = [service.resposta(q) for q in db.query(Quadrinho).all()]
    desejos = [resposta(q) for q in db.query(Desejo).all()]
    return await recomendar(acervo, desejos, modo=dados.modo, rodada=dados.rodada, vistos=dados.vistos, atualizar=dados.atualizar)
