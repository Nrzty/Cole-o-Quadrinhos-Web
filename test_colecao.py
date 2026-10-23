import os,tempfile,unittest,asyncio
from unittest.mock import patch,AsyncMock
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db').replace('\\','/')
from app.main import app
from app.database import SessionLocal,migrar_banco
from app.services.quadrinho_service import QuadrinhoService
from app.schemas import QuadrinhoManualCreate
from app.services.classificacao import identificar_colecao
from sqlalchemy import create_engine,text
from fastapi import HTTPException

class Tests(unittest.TestCase):
 def test_cadastro_sem_isbn_ano(self):
  with SessionLocal() as db, patch('app.services.quadrinho_service.buscar_capa',new=AsyncMock(return_value=None)):
   service=QuadrinhoService(db)
   for nome in ['Absolute Batman','A Saga do Batman']:
    q=asyncio.run(service.adicionar_manual(QuadrinhoManualCreate(titulo=nome,ano='',isbn='')))
    self.assertIsNone(q['isbn']);self.assertIsNone(q['ano'])
   self.assertEqual(len(service.listar()),2)
 def test_duplicado(self):
  with SessionLocal() as db, patch('app.services.quadrinho_service.buscar_capa',new=AsyncMock(return_value=None)):
   service=QuadrinhoService(db);data=QuadrinhoManualCreate(titulo='Teste',isbn='978-1401207526')
   asyncio.run(service.adicionar_manual(data))
   with self.assertRaises(HTTPException) as erro:asyncio.run(service.adicionar_manual(data))
   self.assertEqual(erro.exception.status_code,409)
 def test_paginacao_e_correcao(self):
  with SessionLocal() as db:
   service=QuadrinhoService(db)
   for i in range(110):asyncio.run(service.adicionar_manual(QuadrinhoManualCreate(titulo=f'Volume {i}',capa_url='https://example.com/a.jpg')))
   self.assertEqual(len(service.listar(0,500)),113)
   self.assertEqual(len(service.listar(100,500)),13)
   q=service.obter(1);q.colecao='Minha coleção';self.assertEqual(service.salvar(q)['colecao'],'Minha coleção')
   q.colecao=None;self.assertEqual(service.salvar(q)['colecao'],'Absolute')
 def test_classificacao(self):
  for titulo,ano,esperado in [('Batman',2025,'Outras coleções'),('Batman 2025 vol. 2',None,'Batman 2025'),('A Saga do Batman',None,'A Saga do Batman'),('Absolute Superman',None,'Absolute'),('Sandman Volume 3',None,'Sandman')]:self.assertEqual(identificar_colecao(titulo,ano),esperado)
 def test_migracao(self):
  old=create_engine('sqlite:///:memory:')
  with old.begin() as c:
   c.execute(text('CREATE TABLE quadrinhos (id INTEGER PRIMARY KEY, isbn VARCHAR UNIQUE)'));c.execute(text("INSERT INTO quadrinhos(isbn) VALUES ('')"))
  with patch('app.database.engine',old):migrar_banco();migrar_banco()
  with old.connect() as c:self.assertIsNone(c.execute(text('SELECT isbn FROM quadrinhos')).scalar());c.execute(text('SELECT colecao FROM quadrinhos'))
 def test_capas_exatas_e_falhas(self):
  import httpx
  from app.services.capas import buscar_capa
  def handle(req):
   if 'openlibrary' in str(req.url):return httpx.Response(200,json={})
   return httpx.Response(200,json={'items':[{'volumeInfo':{'industryIdentifiers':[{'identifier':'9781401207526'}],'imageLinks':{'thumbnail':'http://example.com/a.jpg'}}}]})
  real=httpx.AsyncClient
  with patch('app.services.capas.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(handle),**kw)):
   self.assertEqual(asyncio.run(buscar_capa('9781401207526')),'https://example.com/a.jpg')
   self.assertIsNone(asyncio.run(buscar_capa('0000000000')))
if __name__=='__main__':unittest.main(verbosity=2)
