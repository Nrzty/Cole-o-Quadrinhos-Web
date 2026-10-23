"""Recomenda conteúdo ainda ausente, em edições brasileiras confirmadas."""
import asyncio
import os
import re
import time
from urllib.parse import urlparse
import httpx
from app.services.classificacao import identificar_colecao
from app.services.capas import url_segura
from app.services.leitura import planejar, corresponde, sobrepoe, serie_volume, limpo
from app.services.catalogo_br import buscar_panini

_cache = {}

def chave_isbn(isbn):
    valor = re.sub(r'[^0-9X]', '', (isbn or '').upper())
    if len(valor) == 10 and valor[:9].isdigit():
        base = '978' + valor[:9]
        return base + str((10 - sum(int(n) * (1 if i % 2 == 0 else 3) for i, n in enumerate(base)) % 10) % 10)
    return valor

def chave_titulo(titulo):
    return limpo(titulo)

def edicao_brasileira(q):
    if q.get('publicacao_br') and urlparse(q.get('fonte_url', '')).hostname == 'panini.com.br':
        return True
    isbn = chave_isbn(q.get('isbn'))
    # Português sozinho não prova publicação no Brasil. A edição também precisa
    # de um ISBN de grupo brasileiro; país de venda não é país de publicação.
    return q.get('idioma') in ('pt', 'pt-BR', 'pt-br') and len(isbn) == 13 and isbn.startswith(('97865', '97885'))

def mesma_edicao_ou_conteudo(a, b):
    if a.get('isbn') and b.get('isbn') and chave_isbn(a['isbn']) == chave_isbn(b['isbn']):
        return True
    sa, sb = serie_volume(a), serie_volume(b)
    return bool(sa and sa == sb) or sobrepoe(a, b)

def classificar(candidatos, acervo, desejos):
    planos = planejar(acervo, desejos)
    resultados = []
    for q in candidatos:
        if not edicao_brasileira(q) or any(mesma_edicao_ou_conteudo(q, x) for x in acervo + desejos):
            continue
        compativeis = [p for p in planos if corresponde(q, p)]
        if not compativeis:
            continue
        plano = max(compativeis, key=lambda p: p['prioridade'])
        if 'serie' in plano:
            q = q | {'tipo': next((x.get('tipo', 'Quadrinho') for x in acervo if (s := serie_volume(x)) and s[0] == plano['serie']), 'Quadrinho')}
        resultados.append(q | {'colecao': q.get('colecao') or identificar_colecao(q['titulo']),
            'motivos': [plano['motivo']], 'pontuacao': plano['prioridade'], 'categoria': plano['categoria'],
            'fonte_relacao': plano.get('fonte_relacao'),
            'chave': chave_isbn(q.get('isbn')) or q.get('fonte_url') or chave_titulo(q['titulo'])})
    # Uma história aparece uma vez, mesmo com vários formatos e ISBNs no catálogo.
    finais = []
    for q in sorted(resultados, key=lambda q: (-q['pontuacao'], q.get('fonte_nome') != 'Panini Brasil', 'omnibus' in limpo(q['titulo']), q['titulo'])):
        if not any(mesma_edicao_ou_conteudo(q, x) for x in finais):
            finais.append(q)
    return finais[:12]

async def buscar_google(client, plano):
    params = {'q': plano['busca'] + ' Panini', 'maxResults': 20, 'printType': 'books', 'langRestrict': 'pt', 'country': 'BR'}
    if os.getenv('GOOGLE_BOOKS_API_KEY'):
        params['key'] = os.environ['GOOGLE_BOOKS_API_KEY']
    res = await client.get('https://www.googleapis.com/books/v1/volumes', params=params)
    res.raise_for_status()
    candidatos = []
    for item in res.json().get('items', []):
        info = item.get('volumeInfo', {})
        ids = info.get('industryIdentifiers', [])
        isbn = next((i.get('identifier') for i in ids if i.get('type') == 'ISBN_13'), None) or next((i.get('identifier') for i in ids if i.get('type') == 'ISBN_10'), None)
        if not isbn or not info.get('title'):
            continue
        titulo = info['title'] + (': ' + info['subtitle'] if info.get('subtitle') else '')
        candidatos.append({'isbn': isbn, 'titulo': titulo, 'autor': ', '.join(info.get('authors', [])),
            'editora': info.get('publisher'), 'ano': int(info['publishedDate'][:4]) if re.match(r'^\d{4}', info.get('publishedDate') or '') else None,
            'capa_url': url_segura(info.get('imageLinks', {}).get('thumbnail')), 'tipo': 'Quadrinho',
            'idioma': info.get('language'), 'fonte_nome': 'Google Books', 'fonte_url': 'https://books.google.com/books?id=' + item['id']})
    return [q for q in candidatos if edicao_brasileira(q) and corresponde(q, plano)]

async def recomendar(acervo, desejos):
    if not acervo:
        return {'itens': [], 'mensagem': 'Adicione quadrinhos à estante para receber recomendações.'}
    assinatura = repr((acervo, desejos))
    cache = _cache.get(assinatura)
    if cache and time.monotonic() - cache[0] < 900:
        return cache[1]
    planos = planejar(acervo, desejos)
    if not planos:
        return {'itens': [], 'mensagem': 'Ainda não identificamos uma sequência ou relação de leitura segura. Confira os nomes das séries e a numeração das edições; não usamos apenas autor ou editora para sugerir compras.'}
    falhas = []
    limite = asyncio.Semaphore(3)
    async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={'User-Agent': 'Estante/1.0 (catalog lookup)'}) as client:
        async def consultar(plano):
            async with limite:
                candidatos = []
                try:
                    candidatos = await buscar_panini(client, plano)
                except (httpx.HTTPError, ValueError, TypeError):
                    falhas.append('Panini Brasil')
                if not candidatos:
                    try:
                        candidatos = await buscar_google(client, plano)
                    except (httpx.HTTPError, ValueError, TypeError):
                        falhas.append('Google Books')
                return candidatos
        lotes = await asyncio.gather(*(consultar(p) for p in planos))
    itens = classificar([q for lote in lotes for q in lote], acervo, desejos)
    mensagem = 'Parte das consultas ao catálogo falhou. Mostramos somente as edições brasileiras confirmadas.' if falhas else ''
    if not itens and not falhas:
        mensagem = 'Não encontramos edições brasileiras confirmadas para os próximos passos identificados. Isso não significa que sua coleção esteja completa.'
    resposta = {'itens': itens, 'mensagem': mensagem}
    if not falhas:
        if len(_cache) > 50:
            _cache.clear()
        _cache[assinatura] = (time.monotonic(), resposta)
    return resposta
