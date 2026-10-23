import re
import unicodedata


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto or '') if not unicodedata.combining(c)).lower()


def identificar_colecao(titulo, ano=None):
    texto = normalizar(titulo)
    if re.search(r'\babsolute\b|\babsoluto\b', texto):
        return 'Absolute'
    if re.search(r'\b(?:a )?saga d[oa] batman\b', texto):
        return 'A Saga do Batman'
    if re.search(r'\bbatman\b.*\b2025\b|\b2025\b.*\bbatman\b', texto):
        return 'Batman 2025'
    for padrao, nome in [
        (r'\ba saga do superman\b', 'A Saga do Superman'),
        (r'\b(?:dc )?compact\b', 'DC Compact'),
        (r'\b(?:dc )?essenciais\b', 'DC Essenciais'),
        (r'\bmarvel (?:essenciais|essentials)\b', 'Marvel Essenciais'),
        (r'\bultimate\b', 'Ultimate'),
    ]:
        if re.search(padrao, texto):
            return nome
    # Agrupa volumes numerados; preserva títulos sem evidência de uma série.
    base = re.sub(r'\s*(?:[-–:#]\s*)?(?:vol(?:ume)?\.?|n[º°o.]|edicao|#)\s*\d+.*$', '', titulo, flags=re.I).strip(' -–:')
    if base and base != titulo:
        return base
    return 'Outras coleções'
