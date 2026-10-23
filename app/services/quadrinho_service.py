from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models import Quadrinho
from app.services.brasil_api import BrasilAPIService
from app.services.capas import buscar_capa, url_segura
from app.services.classificacao import identificar_colecao

class QuadrinhoService:
    def __init__(self, db: Session):
        self.db = db

    def resposta(self, q):
        return {c.name: getattr(q, c.name) for c in q.__table__.columns} | {
            'colecao': q.colecao or identificar_colecao(q.titulo, q.ano),
            'colecao_manual': bool(q.colecao)
        }

    def salvar(self, q):
        self.db.add(q)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(409, 'ISBN já cadastrado na coleção.')
        self.db.refresh(q)
        return self.resposta(q)

    async def adicionar(self, dados):
        isbn = dados.isbn
        if self.db.query(Quadrinho).filter(Quadrinho.isbn == isbn).first():
            raise HTTPException(409, 'Quadrinho já cadastrado na coleção!')
        info = await BrasilAPIService.fetch_isbn(isbn)
        autores = info.get('authors') or []
        capa = url_segura(info.get('cover_url')) or await buscar_capa(isbn)
        return self.salvar(Quadrinho(isbn=isbn, titulo=info.get('title') or 'Título desconhecido',
            autor=', '.join(autores) if isinstance(autores, list) else str(autores),
            editora=info.get('publisher'), ano=info.get('year'), tipo=dados.tipo, capa_url=capa))

    async def adicionar_manual(self, dados):
        valores = dados.model_dump()
        valores['colecao'] = (dados.colecao or '').strip() or None
        if not dados.capa_url:
            valores['capa_url'] = await buscar_capa(dados.isbn)
        return self.salvar(Quadrinho(**valores))

    def listar(self, skip=0, limit=100):
        return [self.resposta(q) for q in self.db.query(Quadrinho).order_by(Quadrinho.id).offset(skip).limit(limit).all()]

    def obter(self, id):
        q = self.db.get(Quadrinho, id)
        if not q:
            raise HTTPException(404, 'Quadrinho não encontrado.')
        return q

    def remover(self, id):
        self.db.delete(self.obter(id))
        self.db.commit()
