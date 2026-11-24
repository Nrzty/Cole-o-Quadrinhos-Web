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
