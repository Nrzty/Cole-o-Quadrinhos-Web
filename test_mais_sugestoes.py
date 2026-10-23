import asyncio, unittest
from unittest.mock import patch,AsyncMock
from app.services.leitura import planejar,explorar,planos_recomendacao,OBRAS,historias
from app.services.recomendacoes import recomendar,_cache,classificar

def candidato(plano):
 titulo=OBRAS[plano['obra']][0] if 'obra' in plano else plano['busca']
 return {'titulo':titulo,'isbn':None,'publicacao_br':True,'idioma':'pt-BR','fonte_url':'https://panini.com.br/'+titulo.replace(' ','-'),'fonte_nome':'Panini Brasil'}
class MaisSugestoesTests(unittest.TestCase):
 def setUp(self):_cache.clear();self.acervo=[{'titulo':'Batman (2025) 01'}]
 def test_volume_61_nao_impoe_comprar_1(self):
  planos=planejar([{'titulo':'A Saga do Batman 61'}],[])
  self.assertEqual([p['volume'] for p in planos if 'volume' in p],[62])
 def test_lacuna_interna_continua(self):
  planos=planejar([{'titulo':'A Saga do Batman 61'},{'titulo':'A Saga do Batman 63'}],[])
  self.assertEqual([p['volume'] for p in planos if 'volume' in p],[62,64])
 def test_explorar_nao_confunde_com_continuacao(self):
  candidato_silencio={'titulo':'Batman: Silêncio (DC de Bolso)','publicacao_br':True,'fonte_url':'https://panini.com.br/silencio'}
  self.assertEqual(classificar([candidato_silencio],self.acervo,[],modo='continuar'),[])
  self.assertEqual(classificar([candidato_silencio],self.acervo,[],modo='explorar')[0]['categoria'],'Explorar nova história')
 def test_explorar_exclui_obras_e_desejos(self):
  planos=explorar([{'titulo':'Batman: Silêncio - Edição Absoluta'}],[{'titulo':'Batman: A Corte das Corujas'}])
  self.assertFalse(any(p['obra'] in ['silencio','corte-corujas'] for p in planos))
 def test_superman_nao_ativa_base_batman(self):
  self.assertFalse(any(p.get('obra')=='ano-um' for p in planejar([{'titulo':'Grandes Astros: Superman'}],[])))
  self.assertGreater(len(explorar([{'titulo':'Superman 01'}],[])),3)
 def test_robin_e_batman_robin_sao_obras_distintas(self):
  from app.services.leitura import sobrepoe,corresponde
  robin={'titulo':'Robin: Ano Um'}
  dupla={'titulo':'Batman & Robin: Ano Um Vol. 01'}
  self.assertFalse(sobrepoe(robin,dupla))
  self.assertFalse(corresponde(dupla,{'obra':'robin-ano-um','exploracao':True}))
 def test_rodadas_sem_repeticao_e_fim(self):
  async def fonte(client,plano):return [candidato(plano)]
  async def run():
   vistos=[];rodada=0;total=[]
   with patch('app.services.recomendacoes.buscar_panini',side_effect=fonte):
    while True:
     r=await recomendar(self.acervo,[],modo='explorar',rodada=rodada,vistos=vistos)
     novas=[q['chave'] for q in r['itens']]
     self.assertFalse(set(novas)&set(vistos));vistos+=novas;total+=r['itens']
     rodada=r['proxima_rodada']
     if not r['tem_mais']:break
    self.assertGreater(len(total),8)
    fim=await recomendar(self.acervo,[],modo='explorar',rodada=rodada,vistos=vistos)
    self.assertEqual(fim['itens'],[]);self.assertFalse(fim['tem_mais'])
  asyncio.run(run())
 def test_atualizar_ignora_cache(self):
  fonte=AsyncMock(return_value=[])
  async def run():
   with patch('app.services.recomendacoes.buscar_panini',fonte),patch('app.services.recomendacoes.buscar_google',new=AsyncMock(return_value=[])):
    await recomendar(self.acervo,[],modo='continuar');n=fonte.await_count
    await recomendar(self.acervo,[],modo='continuar');self.assertEqual(fonte.await_count,n)
    await recomendar(self.acervo,[],modo='continuar',atualizar=True);self.assertGreater(fonte.await_count,n)
  asyncio.run(run())
if __name__=='__main__':unittest.main(verbosity=2)
