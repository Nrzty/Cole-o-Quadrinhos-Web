import unittest
from datetime import date
from decimal import Decimal
import sys

if __package__:
    from . import compras as c
else:
    import compras as c

sys.path.insert(0, str(c.PASTA.parent))
from app.services import leitura


class MotorTest(unittest.TestCase):
    def executar(self, acervo, ofertas, desejos=(), compras=None, historico=None, saldo="20"):
        cfg = c.configurar(c.PASTA / "config.toml")
        rows = [dict(titulo=t, url=t, preco_atual=Decimal("9.99"), economia=None,
                     desconto_pct=None, preco_referencia=None, **extra) for t, extra in ofertas]
        return c.recomendar(rows, leitura, [dict(id=i+1, titulo=t) for i,t in enumerate(acervo)],
                            [dict(titulo=t) for t in desejos], compras or {}, date(2026,1,1),
                            historico or {}, cfg, Decimal(saldo))

    def test_volumes_desejo_sobreposto_e_orcamento(self):
        titulos = [f"Absolute Batman {n:02}" for n in (1,2,3,4,5)]
        r = self.executar([titulos[0], titulos[3]], [(t,{}) for t in reversed(titulos)], [titulos[1]])
        self.assertEqual(r["descartes"]["JA_POSSUO"], 2)
        self.assertEqual([x["categoria"] for x in r["ranking"]], ["WISHLIST","LACUNA","CONTINUACAO"])
        self.assertEqual(r["ranking"][0]["componentes"]["continuidade"]["valor"], 1)
        self.assertEqual(r["saldo"], Decimal(".02"))
        self.assertEqual(len(r["cesta"]), 2)

    def test_ano_um_e_estoque(self):
        r = self.executar(["Batman: Ano Um"], [("Arqueiro Verde: Ano Um",{}),
                         ("Batman: Ano Um",{}), ("Batman: Silêncio",{"disponibilidade":"indisponível"})])
        self.assertEqual(r["descartes"]["JA_POSSUO"], 1)
        self.assertEqual(r["descartes"]["INDISPONIVEL"], 1)

    def test_revisao_ortografia(self):
        r = self.executar(["Batman: Gotham Central"], [("Batman: Gotam Centrl",{})])
        self.assertEqual(len(r["revisar"]), 1)
        self.assertFalse(r["cesta"])

    def test_historico_decaimento_e_score(self):
        t = "Batman: Silêncio"
        r = self.executar(["Batman: Ano Um","Absolute Batman 1"], [(t,{"unidades":"2"})],
                          compras={"1":{"data":"2025-01-01","preco_pago":10},
                                   "2":{"data":"2026-01-01","preco_pago":40}}, historico={t:Decimal(12)})
        self.assertEqual(r["media_paga"],30)
        item = r["ranking"][0]
        for k in ("urgencia","historico","preco_relativo"):
            self.assertEqual(item["componentes"][k]["valor"],1)
        self.assertAlmostEqual(item["score"], sum(v["pontos"] for v in item["componentes"].values()))


if __name__ == "__main__":
    unittest.main()
