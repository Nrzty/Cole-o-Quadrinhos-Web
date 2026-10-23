from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import QuadrinhoCreate, QuadrinhoResponse, QuadrinhoManualCreate
from app.services.quadrinho_service import QuadrinhoService

router = APIRouter(prefix="/api/quadrinhos", tags=["Quadrinhos"])

@router.post("/", response_model=QuadrinhoResponse)
async def adicionar_quadrinho(quadrinho: QuadrinhoCreate, db: Session = Depends(get_db)):
    """Rota para adicionar um quadrinho (acessa a Brasil API)"""
    service = QuadrinhoService(db)
    return await service.adicionar(quadrinho)

@router.post("/manual", response_model=QuadrinhoResponse)
async def adicionar_quadrinho_manual(quadrinho: QuadrinhoManualCreate, db: Session = Depends(get_db)):
    """Rota para adicionar manualmente"""
    service = QuadrinhoService(db)
    return await service.adicionar_manual(quadrinho)

@router.get("/", response_model=list[QuadrinhoResponse])
def listar_quadrinhos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Rota para listar todos os quadrinhos"""
    service = QuadrinhoService(db)
    return service.listar(skip, limit)

from pydantic import BaseModel

class CapaUpdate(BaseModel):
    capa_url: str

@router.delete("/{quadrinho_id}")
def remover_quadrinho(quadrinho_id: int, db: Session = Depends(get_db)):
    """Rota para deletar um quadrinho"""
    service = QuadrinhoService(db)
    service.remover(quadrinho_id)
    return {"mensagem": "Quadrinho removido com sucesso!"}

@router.patch("/{quadrinho_id}/capa")
def atualizar_capa(quadrinho_id: int, dados: CapaUpdate, db: Session = Depends(get_db)):
    """Rota para atualizar manualmente a URL da capa"""
    from app.models import Quadrinho
    quadrinho = db.query(Quadrinho).filter(Quadrinho.id == quadrinho_id).first()
    if not quadrinho:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Quadrinho não encontrado.")
    quadrinho.capa_url = dados.capa_url
    db.commit()
    return {"mensagem": "Capa atualizada!"}
