"""Catálogo Panini Brasil: só gera candidatos a partir de páginas de produto reais."""
import html
import json
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from app.services.capas import url_segura
from app.services.leitura import corresponde


class Pagina(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.produtos = []
        self.script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'product-item-link' in attrs.get('class', '').split():
            url = urljoin('https://panini.com.br/', attrs.get('href', ''))
            if urlparse(url).hostname == 'panini.com.br' and url not in self.links:
                self.links.append(url)
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.script = []

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.script is not None:
            try:
                self.visitar(json.loads(''.join(self.script)))
            except (ValueError, TypeError):
                pass
            self.script = None

    def visitar(self, data):
        if isinstance(data, list):
            for x in data:
                self.visitar(x)
        elif isinstance(data, dict):
            tipos = data.get('@type', [])
            if tipos == 'Product' or isinstance(tipos, list) and 'Product' in tipos:
                self.produtos.append(data)
            if '@graph' in data:
                self.visitar(data['@graph'])


def produto_br(data, url):
    if urlparse(url).hostname != 'panini.com.br' or not data.get('name'):
        return None
    imagem = data.get('image', [])
    if isinstance(imagem, list):
        imagem = imagem[0] if imagem else None
    if isinstance(imagem, dict):
        imagem = imagem.get('url')
    return {'titulo': html.unescape(data['name']), 'isbn': data.get('isbn') or None,
        'autor': None, 'editora': 'Panini Brasil', 'ano': None, 'tipo': 'Quadrinho',
        'capa_url': url_segura(imagem), 'idioma': 'pt-BR', 'publicacao_br': True,
        'fonte_url': url, 'fonte_nome': 'Panini Brasil', 'descricao': html.unescape(data.get('description', ''))}


async def buscar_panini(client, plano):
    res = await client.get('https://panini.com.br/catalogsearch/result/', params={'q': plano['busca']})
    res.raise_for_status()
    pagina = Pagina()
    pagina.feed(res.text)
    candidatos = []
    # Nunca usa os dados de produtos relacionados como se fossem o produto principal.
    for url in pagina.links[:4]:
        res = await client.get(url)
        res.raise_for_status()
        if urlparse(str(res.url)).hostname != 'panini.com.br':
            continue
        produto = Pagina()
        produto.feed(res.text)
        for data in produto.produtos:
            q = produto_br(data, str(res.url))
            if q and corresponde(q, plano):
                candidatos.append(q)
    return candidatos
