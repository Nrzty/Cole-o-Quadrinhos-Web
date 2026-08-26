from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Quadrinho
from app.schemas import QuadrinhoCreate, QuadrinhoManualCreate
from app.services.brasil_api import BrasilAPIService
import httpx

class QuadrinhoService:
    def __init__(self, db: Session):
        self.db = db

    async def adicionar(self, dados: QuadrinhoCreate):
        """Adiciona um novo quadrinho na coleção."""
        isbn_limpo = dados.isbn.replace("-", "").strip()
        
        # Verifica se existe no banco
        db_quadrinho = self.db.query(Quadrinho).filter(Quadrinho.isbn == isbn_limpo).first()
        if db_quadrinho:
            raise HTTPException(status_code=400, detail="Quadrinho já cadastrado na coleção!")
            
        # Busca dados na API externa
        api_data = await BrasilAPIService.fetch_isbn(isbn_limpo)
        
        # Formata os autores
        autores_lista = api_data.get("authors", [])
        autores = ", ".join(autores_lista) if isinstance(autores_lista, list) else str(autores_lista)
        
        # Extrai a capa inicial da Brasil API (se houver)
        capa_url = api_data.get("cover_url", "")
        
        # Fallback: Google Books API autenticada
        import os
        api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
        
        if not capa_url and api_key:
            try:
                gb_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}&key={api_key}"
                async with httpx.AsyncClient() as client:
                    gb_response = await client.get(gb_url, follow_redirects=True)
                    if gb_response.status_code == 200:
                        gb_data = gb_response.json()
                        if gb_data.get("totalItems", 0) > 0:
                            img_links = gb_data["items"][0].get("volumeInfo", {}).get("imageLinks", {})
                            capa_url = img_links.get("thumbnail", "").replace("http://", "https://")
            except Exception:
                pass # Se falhar, ignora e deixa sem imagem
                
        # Cria a entidade do banco de dados
        novo_quadrinho = Quadrinho(
            isbn=isbn_limpo,
            titulo=api_data.get("title", "Título Desconhecido"),
            autor=autores,
            editora=api_data.get("publisher", "Editora Desconhecida"),
            ano=api_data.get("year"),
            tipo=dados.tipo,
            capa_url=capa_url
        )
        
        self.db.add(novo_quadrinho)
        self.db.commit()
        self.db.refresh(novo_quadrinho)
        return novo_quadrinho

    async def adicionar_manual(self, dados: QuadrinhoManualCreate):
        """Adiciona um novo quadrinho manualmente sem depender de API externa."""
        isbn_limpo = dados.isbn.replace("-", "").strip() if dados.isbn else ""
        
        if isbn_limpo:
            db_quadrinho = self.db.query(Quadrinho).filter(Quadrinho.isbn == isbn_limpo).first()
            if db_quadrinho:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="ISBN já cadastrado na coleção!")
                
        novo_quadrinho = Quadrinho(
            isbn=isbn_limpo,
            titulo=dados.titulo,
            autor=dados.autor,
            editora=dados.editora,
            ano=dados.ano,
            tipo=dados.tipo,
            capa_url=dados.capa_url
        )
        
        self.db.add(novo_quadrinho)
        self.db.commit()
        self.db.refresh(novo_quadrinho)
        return novo_quadrinho

    def listar(self, skip: int = 0, limit: int = 100):
        """Lista quadrinhos salvos na coleção."""
        return self.db.query(Quadrinho).offset(skip).limit(limit).all()

    def remover(self, quadrinho_id: int):
        """Remove um quadrinho pelo ID."""
        quadrinho = self.db.query(Quadrinho).filter(Quadrinho.id == quadrinho_id).first()
        if not quadrinho:
            raise HTTPException(status_code=404, detail="Quadrinho não encontrado.")
        self.db.delete(quadrinho)
        self.db.commit()
        return True
