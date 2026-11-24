import os,tempfile,unittest
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db').replace('\\','/')
from app.database import normalizar_url_banco
from sqlalchemy import create_engine
class DriverTests(unittest.TestCase):
 def test_postgres_driver(self):
  for scheme in ['postgres','postgresql','postgresql+psycopg','postgresql+psycopg2']:
   with self.subTest(scheme=scheme):
    url=normalizar_url_banco(scheme+'://user:pass@localhost:5432/db?sslmode=require')
    engine=create_engine(url)
    self.assertEqual(engine.dialect.driver,'psycopg2')
    self.assertEqual(engine.url.query['sslmode'],'require')
    self.assertEqual(engine.url.password,'pass')
    engine.dispose()
 def test_sqlite(self):
  self.assertEqual(normalizar_url_banco('sqlite:///:memory:'),'sqlite:///:memory:')
if __name__=='__main__':unittest.main(verbosity=2)
