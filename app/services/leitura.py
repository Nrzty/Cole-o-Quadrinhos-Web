"""Identidade de conteúdo e relações de leitura, independentes do acabamento."""
import re
from app.services.classificacao import normalizar

FONTES = {
    'batman-2025': 'https://panini.com.br/batman-2025-02',
    'long-victory': 'https://www.dc.com/graphic-novels/batman-dark-victory-1999/batman-dark-victory',
    'cidade-eterna': 'https://www.dc.com/comics/catwoman-when-in-rome-2004/catwoman-when-in-rome-1',
}
OBRAS = {
    'ano-um': ('Batman: Ano Um', r'\b(?:ano um|year one)\b'),
    'longo-dia': ('Batman: O Longo Dia das Bruxas', r'\b(?:o longo dia das bruxas|the long halloween)\b'),
    'vitoria-sombria': ('Batman: Vitória Sombria', r'\b(?:vitoria sombria|dark victory)\b'),
    'cidade-eterna': ('Mulher-Gato: Cidade Eterna', r'\b(?:cidade eterna|when in rome)\b'),
    'cavaleiro-trevas': ('Batman: O Cavaleiro das Trevas', r'\b(?:(?:o )?cavaleiro das trevas|(?:the )?dark knight returns)\b'),
    'cavaleiro-contra-ataca': ('Batman: O Cavaleiro das Trevas Contra-Ataca', r'\b(?:cavaleiro das trevas contra ataca|dark knight strikes again)\b'),
    'raca-superior': ('Batman: O Cavaleiro das Trevas III — A Raça Superior', r'\b(?:raca superior|master race)\b'),
    'piada-mortal': ('Batman: A Piada Mortal', r'\b(?:piada mortal|killing joke)\b'),
}


def limpo(titulo):
    return re.sub(r'[^a-z0-9]+', ' ', normalizar(titulo)).strip()


def parte(titulo):
    m = re.search(r'\b(?:parte|volume|vol|livro)\s*(\d+)\b', limpo(titulo))
    return int(m[1]) if m else None


def historias(q):
    titulo = limpo(q['titulo'])
    # Um omnibus pode conter várias histórias, mesmo sem listá-las no título.
    if 'batman por jeph loeb e tim sale' in titulo:
        return {('longo-dia', None), ('vitoria-sombria', None), ('cidade-eterna', None)}
    ids = {key for key, (_, pattern) in OBRAS.items() if re.search(pattern, titulo)}
    if 'cavaleiro-contra-ataca' in ids or 'raca-superior' in ids:
        ids.discard('cavaleiro-trevas')
    # Especiais e continuações não equivalem automaticamente à obra original.
    if re.search(r'\b(?:especial|ultimo dia das bruxas|last halloween)\b', titulo):
        ids.discard('longo-dia')
    if ids:
        return {(key, parte(titulo)) for key in ids}
    titulo = re.sub(r'\b(?:edicao (?:absoluta|definitiva|especial|de luxo|de colecionador)|dc de bolso|dc compact|capa dura|capa mole|capa variante|reimpressao|nova edicao)\b', '', titulo)
    return {('titulo:' + ' '.join(titulo.split()), None)}


def sobrepoe(a, b):
    return any(x == y and (pa is None or pb is None or pa == pb) for x, pa in historias(a) for y, pb in historias(b))


def serie_volume(q):
    titulo = limpo(q['titulo'])
    # O ano no nome distingue a revista; o ano de publicação sozinho não basta.
    if re.search(r'^batman 2025\b', titulo) or q.get('colecao') == 'Batman 2025':
        serie = 'Batman 2025'
        base = re.sub(r'^batman\s*(?:2025)?\s*', '', titulo)
    elif titulo.startswith('a saga do batman ') or titulo.startswith('saga do batman '):
        serie, base = 'A Saga do Batman', re.sub(r'^(?:a )?saga do batman\s*', '', titulo)
    elif re.match(r'^absolute (?:batman|superman|mulher maravilha|flash|lanterna verde)\b', titulo):
        m = re.match(r'^(absolute (?:batman|superman|mulher maravilha|flash|lanterna verde))\s*(.*)', titulo)
        serie, base = m[1].title(), m[2]
    else:
        m = re.match(r'^(.*?)\s+(?:volume|vol|parte|n)\s*(\d+)\b', titulo)
        if not m:
            return None
        return m[1], int(m[2])
    # Não mistura fases que reiniciaram a numeração.
    if re.search(r'\b(?:fase|temporada|serie|etapa)\b', base):
        return None
    m = re.match(r'(?:(?:vol|volume|n|numero)\s*)?(\d+)\b', base)
    return (serie, int(m[1])) if m else None


def planejar(acervo, desejos):
    series = {}
    for q in acervo:
        item = serie_volume(q)
        if item:
            series.setdefault(item[0], set()).add(item[1])
    planos = []
    for serie, volumes in sorted(series.items()):
        desejados = {s[1] for q in desejos if (s := serie_volume(q)) and s[0] == serie}
        maximo = max(volumes)
        faltantes = [n for n in range(1, maximo) if n not in volumes and n not in desejados]
        # Só procura o próximo número, sem inventar uma edição ou saltar adiante.
        alvos = faltantes[:1] + ([maximo + 1] if maximo + 1 not in desejados else [])
        for n in alvos:
            lacuna = n < maximo
            planos.append({'busca': f'{serie} {n:02}', 'serie': serie, 'volume': n,
                'prioridade': 120 if lacuna else 110, 'categoria': 'Volume faltante' if lacuna else 'Continuar coleção',
                'motivo': f'Você possui os números {", ".join(map(str, sorted(volumes)))} de {serie}. ' + (f'O número {n} não está na sua estante.' if lacuna else f'O número {n} é o próximo após o {maximo}.'),
                'fonte_relacao': FONTES['batman-2025'] if serie == 'Batman 2025' else None})
    completas = {obra for q in acervo for obra, p in historias(q) if p is None}
    tem_batman = any('batman' in limpo(q['titulo']) or any(k in OBRAS for k, _ in historias(q)) for q in acervo)
    relações = [
        ('vitoria-sombria', 'longo-dia', 100, 'Continuação de história', 'Vitória Sombria dá sequência a O Longo Dia das Bruxas, incluindo o desenvolvimento de Harvey Dent e a chegada de Dick Grayson.', FONTES['long-victory']),
        ('longo-dia', 'ano-um', 90, 'Aprofundar leitura', 'Uma leitura complementar para a fase inicial do Batman após Ano Um, com foco no trabalho de detetive e na transformação de Gotham. Não é uma continuação direta de Ano Um.', None),
        ('cidade-eterna', 'vitoria-sombria', 80, 'Leitura paralela', 'Uma história paralela da Mulher-Gato ligada aos acontecimentos de Vitória Sombria.', FONTES['cidade-eterna']),
    ]
    for alvo, origem, pontos, categoria, motivo, fonte in relações:
        if origem in completas and alvo not in completas:
            planos.append({'busca': OBRAS[alvo][0], 'obra': alvo, 'prioridade': pontos, 'categoria': categoria, 'motivo': motivo, 'fonte_relacao': fonte})
    if tem_batman and 'ano-um' not in completas:
        planos.append({'busca': OBRAS['ano-um'][0], 'obra': 'ano-um', 'prioridade': 70, 'categoria': 'Base do personagem', 'motivo': 'Ano Um apresenta o início da carreira de Bruce Wayne e a relação com Gordon. É uma opção para aprofundar a base do personagem, não um pré-requisito para toda história.', 'fonte_relacao': None})
    return sorted(planos, key=lambda p: -p['prioridade'])[:6]


def corresponde(q, plano):
    if 'serie' in plano:
        return serie_volume(q) == (plano['serie'], plano['volume'])
    return (plano['obra'], None) in historias(q)
