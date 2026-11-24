import unittest,asyncio,json
from unittest.mock import AsyncMock,patch
from app.services.recomendacoes import classificar,edicao_brasileira,recomendar,_cache
from app.services.leitura import historias,sobrepoe,serie_volume,planejar
from app.services.classificacao import identificar_colecao
from app.services.catalogo_br import Pagina,produto_br

def q(titulo,**kw):
 return dict(titulo=titulo,isbn=None,idioma='pt-BR',publicacao_br=True,fonte_url='https://panini.com.br/produto-teste',fonte_nome='Panini Brasil',**kw)
class LeituraTests(unittest.TestCase):
 def setUp(self):_cache.clear()
 def test_mesma_historia_outro_formato(self):
  a=q('Batman: O Cavaleiro das Trevas (DC de Bolso)')
  for titulo in ['Batman: O Cavaleiro das Trevas - Edição Absoluta','Batman: Cavaleiro das Trevas (Edição Definitiva)','Batman: The Dark Knight Returns']:
   self.assertTrue(sobrepoe(a,q(titulo)))
  self.assertFalse(sobrepoe(a,q('Batman: O Cavaleiro das Trevas Contra-Ataca')))
  self.assertFalse(sobrepoe(a,q('Batman: O Cavaleiro das Trevas III - A Raça Superior')))
 def test_partes_nao_sao_completas(self):
  self.assertFalse(sobrepoe(q('O Longo Dia das Bruxas vol. 1'),q('O Longo Dia das Bruxas vol. 2')))
  self.assertTrue(sobrepoe(q('O Longo Dia das Bruxas vol. 1'),q('O Longo Dia das Bruxas edição definitiva')))
  self.assertFalse(any(p.get('obra')=='vitoria-sombria' for p in planejar([q('O Longo Dia das Bruxas vol. 1')],[])))
 def test_omnibus_conteudo(self):
  acervo=[q('Batman por Jeph Loeb e Tim Sale (DC Omnibus)')]
  for titulo in ['Batman: O Longo Dia das Bruxas','Batman: Vitória Sombria','Mulher-Gato: Cidade Eterna']:
   self.assertTrue(sobrepoe(acervo[0],q(titulo)))
  self.assertEqual(classificar([q('Batman: Vitória Sombria')],acervo,[]),[])
 def test_prioriza_lacuna_e_proximo(self):
  acervo=[q('A Saga do Batman 01'),q('A Saga do Batman 03'),q('Batman (2025) 01'),q('Batman: Ano Um'),q('O Cavaleiro das Trevas DC de Bolso')]
  candidatos=[q('A Saga do Batman 02'),q('A Saga do Batman 04'),q('Batman (2025) 02'),q('Batman (2025) 07'),q('Batman: O Longo Dia das Bruxas'),q('Batman: Vitória Sombria'),q('O Cavaleiro das Trevas - Edição Absoluta'),q('Absolute Superman 01')]
  resultado=classificar(candidatos,acervo,[])
  self.assertEqual(resultado[0]['titulo'],'A Saga do Batman 02')
  self.assertEqual({x['titulo'] for x in resultado},{'A Saga do Batman 02','A Saga do Batman 04','Batman (2025) 02','Batman: O Longo Dia das Bruxas'})
  self.assertTrue(all(x['motivos'] for x in resultado))
 def test_vitoria_depois_longo(self):
  resultado=classificar([q('Batman: Vitória Sombria')],[q('Batman: O Longo Dia das Bruxas')],[])
  self.assertEqual(resultado[0]['categoria'],'Continuação de história')
 def test_sem_recompra_e_desejos(self):
  acervo=[q('Batman: Ano Um')]
  candidatos=[q('Batman: O Longo Dia das Bruxas (DC de Bolso)'),q('Batman: O Longo Dia das Bruxas - Edição Absoluta')]
  self.assertEqual(len(classificar(candidatos,acervo,[])),1)
  self.assertEqual(classificar(candidatos,acervo,[q('Batman: O Longo Dia das Bruxas')]),[])
 def test_absolute_nao_e_acabamento(self):
  self.assertEqual(identificar_colecao('Absolute Batman 01'),'Absolute')
  self.assertNotEqual(identificar_colecao('O Cavaleiro das Trevas - Edição Absoluta'),'Absolute')
  self.assertIsNone(serie_volume(q('Batman',ano=2025)))
  self.assertEqual(serie_volume(q('Batman (2025) Vol. 02')),('Batman 2025',2))
  self.assertNotEqual(serie_volume(q('Absolute Batman 02')),serie_volume(q('Absolute Superman 02')))
  self.assertIsNone(serie_volume(q('A Saga do Batman - Segunda Série 01')))
 def test_ingles_e_portugues_sem_evidencia_br(self):
  for idioma,isbn in [('en','9786555123450'),('pt','9789891234567'),(None,'9786555123450')]:
   self.assertFalse(edicao_brasileira(dict(titulo='Batman',idioma=idioma,isbn=isbn)))
  self.assertTrue(edicao_brasileira(dict(idioma='pt',isbn='9786555123450')))
 def test_sem_recomendacao_por_autor(self):
  self.assertEqual(classificar([q('Batman: história aleatória',autor='Frank Miller')],[q('O Cavaleiro das Trevas',autor='Frank Miller')],[]),[])
 def test_parser_catalogo_real(self):
  data={'@type':'Product','name':'Batman (2025) 02','isbn':'9786525941509','image':['https://example.com/capa.jpg']}
  pagina=Pagina();pagina.feed('<script type="application/ld+json">'+json.dumps(data)+'</script>')
  self.assertEqual(len(pagina.produtos),1)
  self.assertTrue(edicao_brasileira(produto_br(pagina.produtos[0],'https://panini.com.br/batman-2025-02')))
  self.assertIsNone(produto_br(data,'https://tiendapanini.com.mx/batman-02'))
 def test_provedor_sem_catalogo_nao_inventa(self):
  with patch('app.services.recomendacoes.buscar_panini',new=AsyncMock(return_value=[])),patch('app.services.recomendacoes.buscar_google',new=AsyncMock(return_value=[])):
   resposta=asyncio.run(recomendar([q('Batman (2025) 01')],[]))
  self.assertEqual(resposta['itens'],[])
  self.assertIn('não significa',resposta['mensagem'])
if __name__=='__main__':unittest.main(verbosity=2)
