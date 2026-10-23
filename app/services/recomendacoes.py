"""Recomenda edições reais do catálogo; não inventa títulos nem volumes."""
import asyncio
import os
import re
import time
from collections import Counter
import httpx
from app.services.classificacao import normalizar, identificar_colecao
from app.services.capas import url_segura

_cache = {}


def chave_isbn(isbn):
    valor = re.sub(r'[^0-9X]', '', (isbn or '').upper())
    if len(valor) == 10:
        base = '978' + valor[:9]
        return base + str((10 - sum(int(n) * (1 if i % 2 == 0 else 3) for i, n in enumerate(base)) % 10) % 10)
    return valor


def chave_titulo(titulo):
    return re.sub(r'[^a-z0-9]+', ' ', normalizar(titulo)).strip()


def classificar(candidatos, acervo, desejos):
    excluidos = acervo + desejos
    isbns = {chave_isbn(q.get('isbn')) for q in excluidos if q.get('isbn')}
    titulos = {chave_titulo(q['titulo']) for q in excluidos}
    colecoes = Counter(q.get('colecao') or identificar_colecao(q['titulo']) for q in acervo)
    autores = Counter(normalizar(a.strip()) for q in acervo for a in (q.get('autor') or '').split(',') if a.strip())
    editoras = {normalizar(q.get('editora')) for q in acervo if q.get('editora')}
    temas = {'batman','superman','wonder woman','mulher maravilha','homem aranha','spider man','x men','sandman','naruto','one piece','dragon ball','demon slayer','jujutsu','berserk','watchmen','vingadores','avengers','flash','lanterna verde','green lantern','hellboy','spawn','akira','bleach','death note'}
    temas_acervo = {t for t in temas if any(t in chave_titulo(q['titulo']) for q in acervo)}
    resultado = []
    vistos = set()
    for q in candidatos:
        isbn = chave_isbn(q.get('isbn'))
        titulo = chave_titulo(q['titulo'])
        if not isbn or isbn in isbns or titulo in titulos or isbn in vistos or titulo in vistos:
            continue
        serie = q.get('colecao') or identificar_colecao(q['titulo'])
        mesma_serie = serie != 'Outras coleções' and serie in colecoes
        temas_comuns = sorted(t for t in temas_acervo if t in titulo)
        categorias = normalizar(' '.join(q.get('categorias', [])))
        if not (mesma_serie or temas_comuns or any(t in categorias for t in ['comics','graphic novels','manga','quadrinhos'])):
            continue
        motivos, pontos = [], 0
        if mesma_serie:
            pontos += 60 + min(colecoes[serie], 5)
            motivos.append('Da coleção ' + serie)
        comuns = [a.strip() for a in (q.get('autor') or '').split(',') if normalizar(a.strip()) in autores]
        if comuns:
            pontos += 25
            motivos.append('Autor que você já coleciona: ' + ', '.join(comuns))
        if temas_comuns:
            pontos += 15
            motivos.append('Personagem ou universo presente na sua estante: ' + ', '.join(temas_comuns))
        if normalizar(q.get('editora')) in editoras:
            pontos += 5
            motivos.append('Editora presente na sua coleção')
        if pontos < 15:
            continue
        vistos.add(isbn)
        vistos.add(titulo)
        resultado.append(q | {'colecao': serie, 'motivos': motivos, 'pontuacao': pontos})
    return sorted(resultado, key=lambda q: (-q['pontuacao'], q['titulo']))[:24]


async def recomendar(acervo, desejos):
    if not acervo:
        return {'itens': [], 'mensagem': 'Adicione quadrinhos à estante para receber recomendações.'}
    assinatura = repr((acervo, desejos))
    cache = _cache.get(assinatura)
    if cache and time.monotonic() - cache[0] < 900:
        return cache[1]
    series = Counter(q.get('colecao') or identificar_colecao(q['titulo']) for q in acervo)
    queries = [nome + ' quadrinhos' for nome, _ in series.most_common() if nome != 'Outras coleções'][:2]
    autores = Counter(a.strip() for q in acervo for a in (q.get('autor') or '').split(',') if a.strip())
    queries += [nome + ' comics' for nome, _ in autores.most_common(2)]
    if not queries:
        queries = [acervo[0]['titulo'] + ' quadrinhos']
    falhas = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        async def consultar(query):
            params = {'q': query, 'maxResults': 30, 'printType': 'books'}
            if os.getenv('GOOGLE_BOOKS_API_KEY'):
                params['key'] = os.environ['GOOGLE_BOOKS_API_KEY']
            try:
                res = await client.get('https://www.googleapis.com/books/v1/volumes', params=params)
                res.raise_for_status()
                return res.json().get('items', [])
            except (httpx.HTTPError, ValueError):
                falhas.append(query)
                return []
        lotes = await asyncio.gather(*(consultar(q) for q in dict.fromkeys(queries)))
    candidatos = []
    for lote in lotes:
        for item in lote:
            info = item.get('volumeInfo', {})
            ids = info.get('industryIdentifiers', [])
            isbn = next((i.get('identifier') for i in ids if i.get('type') == 'ISBN_13'), None) or next((i.get('identifier') for i in ids if i.get('type') == 'ISBN_10'), None)
            if not isbn or not info.get('title'):
                continue
            titulo = info['title'] + (': ' + info['subtitle'] if info.get('subtitle') else '')
            candidatos.append({'isbn': isbn, 'titulo': titulo, 'autor': ', '.join(info.get('authors', [])),
                'editora': info.get('publisher'), 'ano': int(info['publishedDate'][:4]) if re.match(r'^\d{4}', info.get('publishedDate', '')) else None,
                'capa_url': url_segura(info.get('imageLinks', {}).get('thumbnail')), 'tipo': 'Mangá' if 'manga' in normalizar(' '.join(info.get('categories', []))) else 'Quadrinho',
                'categorias': info.get('categories', []), 'fonte_url': 'https://books.google.com/books?id=' + item['id']})
    itens = classificar(candidatos, acervo, desejos)
    mensagem = 'Algumas consultas ao catálogo falharam. Tente novamente mais tarde.' if falhas else ''
    if not itens and not mensagem:
        mensagem = 'Não encontramos novas edições compatíveis nas consultas ao catálogo. Você pode adicionar desejos manualmente.'
    resposta = {'itens': itens, 'mensagem': mensagem}
    if not falhas:
        if len(_cache) > 50:
            _cache.clear()
        _cache[assinatura] = (time.monotonic(), resposta)
    return resposta
