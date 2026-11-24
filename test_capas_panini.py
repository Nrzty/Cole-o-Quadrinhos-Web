import unittest

import httpx
from app.services.catalogo_br import buscar_capa_panini


class CapasPaniniTest(unittest.IsolatedAsyncioTestCase):
    async def buscar(self, isbn=None, titulo="Absolute Batman 1", isbn_ficha="9781401207526", variante=False):
        def pagina(req):
            if req.url.path.startswith("/catalogsearch"):
                cards = [("a", "Absolute Batman 01"), ("b", "Absolute Batman 02")]
                if variante:
                    cards.append(("c", "Absolute Batman 01"))
                html = "".join(f'<div class="product-item"><a class="product-item-link" href="/{k}">{t}</a>'
                               f'<img class="product-image-photo" src="/media/{k}.jpg"></div>' for k, t in cards)
            else:
                html = f'''<h1>Absolute Batman 01</h1><meta property="og:image" content="/media/grande.jpg">
                    <table id="product-attribute-specs-table"><tr><th>ISBN</th><td>{isbn_ficha}</td></tr></table>'''
            return httpx.Response(200, text=html)
        async with httpx.AsyncClient(transport=httpx.MockTransport(pagina)) as client:
            return await buscar_capa_panini(client, isbn, titulo)

    async def test_titulo_confirmado_preserva_volume(self):
        self.assertEqual(await self.buscar(), "https://panini.com.br/media/a.jpg")
        self.assertIsNone(await self.buscar(titulo="Absolute Batman 3"))
        self.assertIsNone(await self.buscar(variante=True))

    async def test_isbn_exige_identidade_da_edicao(self):
        self.assertEqual(await self.buscar(isbn="1-4012-0752-9"), "https://panini.com.br/media/grande.jpg")
        self.assertIsNone(await self.buscar(isbn="9780000000002"))
