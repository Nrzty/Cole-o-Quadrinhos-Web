import os,tempfile,unittest,asyncio
from unittest.mock import patch,AsyncMock
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db').replace('\\','/')
from fastapi.testclient import TestClient
from app.main import app
from app.services.recomendacoes import classificar,chave_isbn,recomendar
class Tests(unittest.TestCase):
 def test_wishlist_lifecycle(self):
  with TestClient(app) as c:
   data={'titulo':'Absolute Batman vol. 2','isbn':'9781401207526','prioridade':1,'notas':'Capa dura','ano':''}
   r=c.post('/api/desejos',json=data);self.assertEqual(r.status_code,200,r.text);id=r.json()['id']
   self.assertEqual(c.post('/api/desejos',json=data).status_code,409)
   self.assertEqual(c.post('/api/desejos',json={'titulo':'x','prioridade':4}).status_code,422)
   data['notas']='Comprar depois';data['prioridade']=3
   self.assertEqual(c.put(f'/api/desejos/{id}',json=data).json()['notas'],'Comprar depois')
   self.assertEqual(len(c.get('/api/desejos').json()),1)
   r=c.post(f'/api/desejos/{id}/adquirir');self.assertEqual(r.status_code,200,r.text)
   self.assertEqual(r.json()['colecao'],'Absolute')
   self.assertEqual(c.get('/api/desejos').json(),[])
   self.assertEqual(c.post('/api/desejos',json=data).status_code,409)
   self.assertEqual(c.post(f'/api/desejos/{id}/adquirir').status_code,404)
   q=c.post('/api/desejos',json={'titulo':'Desejo sem ISBN'}).json()
   self.assertEqual(c.delete('/api/desejos/'+str(q['id'])).status_code,200)
   self.assertEqual(c.get('/').status_code,200)
 def test_ranking_and_exclusions(self):
  acervo=[{'titulo':'Absolute Batman vol. 1','colecao':'Absolute','autor':'Scott Snyder','editora':'Panini','isbn':'9781401207526'}]
  def q(titulo,isbn,autor='Outro',colecao='Outras coleções'):return dict(titulo=titulo,isbn=isbn,autor=autor,colecao=colecao,editora='Outra',categorias=['Comics & Graphic Novels'])
  candidatos=[q('Absolute Superman vol. 1','9780000000001',colecao='Absolute'),q('Batman: Outra história','9780000000002'),q('Desejado','9780000000003',autor='Scott Snyder'),q('Duplicado','1401207529'),q('Receitas','9780000000004'),q('Mesmo título','9780000000005','Scott Snyder'),q('Mesmo título','9780000000006','Scott Snyder')]
  resultados=classificar(candidatos,acervo,[{'titulo':'Desejado','isbn':'9780000000003'}])
  self.assertEqual(resultados[0]['titulo'],'Absolute Superman vol. 1')
  self.assertEqual(len(resultados),3)
  self.assertTrue(all(x['motivos'] for x in resultados))
  self.assertEqual(chave_isbn('1401207529'),'9781401207526')
 def test_catalog_success(self):
  import httpx
  payload={'items':[{'id':'abc','volumeInfo':{'title':'Absolute Superman vol. 2','authors':['Jason Aaron'],'publisher':'Panini','publishedDate':'2025-01','industryIdentifiers':[{'type':'ISBN_13','identifier':'9780000000099'}],'categories':['Comics & Graphic Novels'],'imageLinks':{'thumbnail':'https://example.com/capa.jpg'}}}]}
  client=AsyncMock();client.__aenter__.return_value=client
  client.get.return_value=httpx.Response(200,json=payload,request=httpx.Request('GET','https://www.googleapis.com/books/v1/volumes'))
  with patch('app.services.recomendacoes.httpx.AsyncClient',return_value=client):
   resposta=asyncio.run(recomendar([{'titulo':'Absolute Batman volume 1','colecao':'Absolute','autor':'Scott Snyder'}],[]))
  self.assertEqual(len(resposta['itens']),1)
  self.assertEqual(resposta['itens'][0]['colecao'],'Absolute')
  self.assertEqual(resposta['itens'][0]['fonte_url'],'https://books.google.com/books?id=abc')
 def test_catalog_failure_and_empty_collection(self):
  import httpx
  self.assertEqual(asyncio.run(recomendar([],[]))['itens'],[])
  client=AsyncMock();client.__aenter__.return_value=client;client.get.side_effect=httpx.ConnectError('offline')
  with patch('app.services.recomendacoes.httpx.AsyncClient',return_value=client):
   resposta=asyncio.run(recomendar([{'titulo':'Batman','autor':'Scott Snyder','isbn':'123'}],[]))
  self.assertEqual(resposta['itens'],[]);self.assertIn('falharam',resposta['mensagem'])
if __name__=='__main__':unittest.main(verbosity=2)
