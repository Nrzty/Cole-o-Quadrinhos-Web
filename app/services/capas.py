import os
import httpx
from sqlalchemy import or_, update


async def preencher_capa(db, registro):
    if registro.capa_url:
        return
    url = await buscar_capa(registro.isbn, registro.titulo)
    if url:
        modelo = type(registro)
        db.execute(update(modelo).where(modelo.id == registro.id,
                   or_(modelo.capa_url.is_(None), modelo.capa_url == "")).values(capa_url=url))
        db.commit()
        db.refresh(registro)


def url_segura(url):
    if isinstance(url, str) and url.startswith(('https://', 'http://')):
        return url.replace('http://', 'https://', 1)
    return None


async def buscar_capa(isbn, titulo=None):
    from app.services.catalogo_br import buscar_capa_panini

    if not (isbn or titulo):
        return None
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        try:
            capa = await buscar_capa_panini(client, isbn, titulo)
            if capa:
                return capa
        except (httpx.HTTPError, ValueError):
            pass
        if not isbn:
            return None
        # Consulta uma edição exata para evitar capas de outros volumes.
        try:
            chave = f'ISBN:{isbn}'
            res = await client.get('https://openlibrary.org/api/books', params={'bibkeys': chave, 'format': 'json', 'jscmd': 'data'})
            res.raise_for_status()
            capa = res.json().get(chave, {}).get('cover', {})
            url = url_segura(capa.get('large') or capa.get('medium'))
            if url:
                return url
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            pass
        try:
            params = {'q': f'isbn:{isbn}', 'maxResults': 5}
            if os.getenv('GOOGLE_BOOKS_API_KEY'):
                params['key'] = os.environ['GOOGLE_BOOKS_API_KEY']
            res = await client.get('https://www.googleapis.com/books/v1/volumes', params=params)
            res.raise_for_status()
            for item in res.json().get('items', []):
                info = item.get('volumeInfo', {})
                ids = [i.get('identifier', '').replace('-', '') for i in info.get('industryIdentifiers', [])]
                if isbn in ids:
                    imagens = info.get('imageLinks', {})
                    url = url_segura(imagens.get('thumbnail') or imagens.get('smallThumbnail'))
                    if url:
                        return url
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            pass
    return None
