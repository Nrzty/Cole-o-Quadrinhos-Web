"""Catálogo Panini Brasil: só gera candidatos a partir de páginas de produto reais."""
import html
import json
import re
from bs4 import BeautifulSoup
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from app.services.capas import url_segura
from app.services.classificacao import chave_isbn
from app.services.leitura import corresponde
from panini.panini import endereco, imagem_capa, normalizar


def titulo_capa(titulo):
    return re.sub(r"\b0+(?=\d)", "", normalizar(titulo or ""))


async def buscar_capa_panini(client, isbn, titulo):
    """Confirma a edição antes de associar uma imagem à estante."""
    busca = await client.get("https://panini.com.br/catalogsearch/result/", params={"q": isbn or titulo})
    busca.raise_for_status()
    base = endereco(str(busca.url))
    soup = BeautifulSoup(busca.text, "html.parser")
    links = {}
    if soup.select_one(".product-info-main"):
        links[base] = None
    else:
        for card in soup.select(".product-item"):
            link = card.select_one("a.product-item-link[href], .product-item-name a[href]")
            if not link or (not isbn and titulo_capa(link.get_text(" ", strip=True)) != titulo_capa(titulo)):
                continue
            url = endereco(urljoin(base, link["href"]))
            links[url] = imagem_capa(card, base)
        if not isbn and len(links) != 1:
            return None
        if not isbn and next(iter(links.values())):
            return next(iter(links.values()))

    for url in list(links)[:4]:
        ficha = busca if url == base else await client.get(url)
        ficha.raise_for_status()
        final = endereco(str(ficha.url))
        pagina = BeautifulSoup(ficha.text, "html.parser")
        nome = pagina.select_one("h1.page-title, h1")
        if not nome:
            continue
        nome = titulo_capa(nome.get_text(" ", strip=True))
        dados = Pagina()
        dados.feed(ficha.text)
        principal = next((p for p in dados.produtos if titulo_capa(p.get("name")) == nome), {})
        if isbn:
            ids = [principal.get(k) for k in ("isbn", "gtin13", "gtin", "gtin12")]
            for linha in pagina.select("#product-attribute-specs-table tr"):
                rotulo, valor = linha.select_one("th"), linha.select_one("td")
                if rotulo and valor and re.search(r"\b(isbn|ean|gtin)\b", rotulo.get_text(" ", strip=True), re.I):
                    ids.append(valor.get_text(strip=True))
            if chave_isbn(isbn) not in {chave_isbn(str(v)) for v in ids if v}:
                continue
        elif nome != titulo_capa(titulo):
            continue
        produto = produto_br(principal, final) or {}
        return imagem_capa(pagina, final, ficha=True) or produto.get("capa_url") or links[url]
    return None


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
