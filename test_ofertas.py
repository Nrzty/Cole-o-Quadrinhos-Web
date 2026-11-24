import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import ofertas


class BuscaPaniniTest(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(ofertas.router)
        self.client = TestClient(app)
        self.url = "https://panini.com.br/dc-comics"

    @patch.object(ofertas, "listar", return_value=[])
    @patch.object(ofertas, "QuadrinhoService")
    @patch.object(ofertas, "baixar")
    def test_campanha_e_ranking_da_estante(self, baixar, service, desejos):
        campanha = "https://panini.com.br/black-friday-panini"
        editoria = campanha + "?editorial=DC"
        service.return_value.listar.return_value = [{"id": 1, "titulo": "Absolute Batman 1"}]
        baixar.side_effect = [
            ('''<script type="text/x-magento-init">{"*":{"Magento_Ui/js/core/app":{"components":{
               "editorialFilter":{"items":[{"label":"DC Comics","url":"?editorial=DC"}]}}}}}</script>''', campanha),
            ('''<ol class="product-items"><li class="product-item"><a class="product-item-link"
               href="/bat1">Absolute Batman 1</a><span data-price-type="finalPrice" data-price-amount="20"></span></li>
               <li class="product-item"><a class="product-item-link" href="/bat2">Absolute Batman 2</a>
               <span data-price-type="finalPrice" data-price-amount="18"></span></li></ol>''', editoria)]
        dados = self.client.post("/api/ofertas/ranking", json={"url": campanha}).json()
        self.assertEqual(dados["editorias"]["DC Comics"], editoria)
        pagina = self.client.post("/api/ofertas/ranking", json={"url": editoria}).json()
        self.assertEqual(len(pagina["produtos"]), 2)
        self.assertEqual([i["categoria"] for i in pagina["ranking"]], ["CONTINUACAO"])
        self.assertGreater(pagina["ranking"][0]["componentes"]["continuidade"]["pontos"], 0)

    @patch.object(ofertas, "baixar")
    def test_dc_pagina_um_preserva_produtos_e_filtro(self, baixar):
        url = "https://panini.com.br/black-friday-panini?editorial=DC+Comics&p=1"
        html = '''<div class="products-grid"><div class="product-item"><strong class="product-item-name">
            <a href="/absolute-batman">Absolute Batman</a></strong><meta itemprop="price" content="19.90">
            </div><div class="product-item"><a class="product-item-link" href="/outro">Outro</a>
            </div></div><div class="pages"><a href="?p=2">Avançar</a></div>'''
        baixar.return_value = (html, url)
        dados = self.client.post("/api/ofertas", json={"url": url}).json()
        self.assertEqual([x["titulo"] for x in dados["itens"]], ["Absolute Batman"])
        self.assertEqual(float(dados["itens"][0]["preco_atual"]), 19.9)
        from urllib.parse import parse_qs, urlsplit
        self.assertEqual(parse_qs(urlsplit(dados["proxima"]).query), {"editorial":["DC Comics"],"p":["2"]})
        self.assertIn("preço", dados["avisos"][0])

    @patch.object(ofertas, "baixar")
    def test_dc_usa_endereco_publicado_pela_campanha(self, baixar):
        base = ofertas.BLACK_FRIDAY
        url = base + "?editorial=DC+Comics&p=1"
        oficial = base + "?editorial=42"
        baixar.side_effect = [
            ("<html></html>", url),
            ('''<script type="text/x-magento-init">{"*":{"Magento_Ui/js/core/app":{"components":{
            "editorialFilter":{"items":[{"label":"DC Comics","url":"?editorial=42"}]}}}}}</script>''', base),
            ('''<ol class="product-items"><li class="product-item"><a class="product-item-link"
              href="/dc">HQ DC</a><span data-price-type="finalPrice" data-price-amount="10"></span>
              </li></ol>''', oficial)]
        dados = self.client.post("/api/ofertas", json={"url": url}).json()
        self.assertEqual(dados["itens"][0]["titulo"], "HQ DC")
        self.assertEqual(baixar.call_args.args, (oficial,))

    @patch.object(ofertas, "baixar")
    def test_listagem_com_proxima(self, baixar):
        baixar.return_value = ('''<ol class="product-items"><li class="product-item">
            <a class="product-item-link" href="/batman">Batman</a>
            <span data-price-type="finalPrice" data-price-amount="30"></span>
            <span data-price-type="oldPrice" data-price-amount="40"></span>
            </li></ol><div class="pages"><a href="?p=2">2</a></div>''', self.url)
        resposta = self.client.post("/api/ofertas", json={"url": self.url})
        self.assertEqual(resposta.status_code, 200)
        data = resposta.json()
        self.assertEqual(data["proxima"], self.url + "?p=2")
        self.assertEqual(float(data["itens"][0]["desconto_pct"]), 25)

    @patch.object(ofertas, "baixar")
    def test_pagina_de_produto(self, baixar):
        baixar.return_value = ('''<h1>Batman</h1><div class="product-info-main">
            <span data-price-type="finalPrice" data-price-amount="19.92"></span>
            <button class="tocart">Comprar</button></div>''', self.url)
        data = self.client.post("/api/ofertas", json={"url": self.url}).json()
        self.assertIsNone(data["proxima"])
        self.assertEqual(data["itens"][0]["disponibilidade"], "compra disponível")
        self.assertEqual(float(data["itens"][0]["preco_atual"]), 19.92)

    @patch.object(ofertas, "baixar")
    def test_url_invalida_e_falha_remota(self, baixar):
        resposta = self.client.post("/api/ofertas", json={"url": "https://example.org/"})
        self.assertEqual(resposta.status_code, 422)
        baixar.assert_not_called()
        baixar.side_effect = OSError()
        self.assertEqual(self.client.post("/api/ofertas", json={"url": self.url}).status_code, 502)
