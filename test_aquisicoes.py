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
 def test_catalog_success(self):
  candidato={'titulo':'Absolute Batman vol. 2','isbn':'9786555123450','idioma':'pt','editora':'Panini Brasil','fonte_nome':'Panini Brasil','fonte_url':'https://panini.com.br/absolute-batman-02'}
  with patch('app.services.recomendacoes.buscar_panini',new=AsyncMock(return_value=[candidato])),patch('app.services.recomendacoes.buscar_google',new=AsyncMock(return_value=[])):
   resposta=asyncio.run(recomendar([{'titulo':'Absolute Batman vol. 1','colecao':'Absolute','autor':'Scott Snyder'}],[]))
  self.assertEqual(len(resposta['itens']),1)
  self.assertEqual(resposta['itens'][0]['categoria'],'Continuar coleção')
 def test_catalog_failure_and_empty_collection(self):
  import httpx
  self.assertEqual(asyncio.run(recomendar([],[]))['itens'],[])
  client=AsyncMock();client.__aenter__.return_value=client;client.get.side_effect=httpx.ConnectError('offline')
  with patch('app.services.recomendacoes.httpx.AsyncClient',return_value=client):
   resposta=asyncio.run(recomendar([{'titulo':'Batman (2025) 01','autor':'Chip Zdarsky','isbn':'123'}],[]))
  self.assertEqual(resposta['itens'],[]);self.assertIn('falhou',resposta['mensagem'])
if __name__=='__main__':unittest.main(verbosity=2)
