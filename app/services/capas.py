import os
import httpx


def url_segura(url):
    if isinstance(url, str) and url.startswith(('https://', 'http://')):
        return url.replace('http://', 'https://', 1)
    return None


async def buscar_capa(isbn):
    if not isbn:
        return None
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
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
