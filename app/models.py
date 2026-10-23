from sqlalchemy import Column, Integer, String
from app.database import Base

class Quadrinho(Base):
    __tablename__ = "quadrinhos"
    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String, unique=True, index=True)
    titulo = Column(String, index=True)
    autor = Column(String)
    editora = Column(String)
    ano = Column(Integer)
    tipo = Column(String, default="Quadrinho")
    capa_url = Column(String)

    colecao = Column(String, nullable=True)


class Desejo(Base):
    __tablename__ = 'desejos'
    id = Column(Integer, primary_key=True)
    isbn = Column(String, unique=True, nullable=True)
    titulo = Column(String, nullable=False)
    autor = Column(String)
    editora = Column(String)
    ano = Column(Integer)
    tipo = Column(String, default='Quadrinho')
    capa_url = Column(String)
    colecao = Column(String)
    prioridade = Column(Integer, default=2)
    notas = Column(String, default='')
