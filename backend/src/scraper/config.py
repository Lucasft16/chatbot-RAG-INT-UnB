"""Configuração e filtro de escopo do crawler.

O escopo tem duas partes: só o host `int.unb.br` (links para `unb.br` ficam de
fora) e só o path `/br/*` (a versão em português; ignora `/en`, `/es`, `/fr`).
"""

from __future__ import annotations

from urllib.parse import urlparse

SEED_URLS: list[str] = [
    "https://int.unb.br/br",
]

# "unb.br" puro NÃO entra: só os subdomínios do INT.
ALLOWED_HOSTS: set[str] = {
    "int.unb.br",
    "www.int.unb.br",
}

# Boa cidadania: identificar o bot e espaçar as requisições.
USER_AGENT = "int-unb-chatbot-portfolio/0.1 (+contato no README)"
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30

ALLOWED_PATH_PREFIX = "/br"

# Conteúdo que muda com frequência (motiva o re-scraping).
DYNAMIC_PATH_PREFIXES: tuple[str, ...] = (
    "/br/selecoes-int/abertas",
    "/br/selecoes-int/convencerradas",
)

# Utilidades do Joomla (login, contato, busca): em escopo, mas só geram ruído.
NON_CONTENT_PATH_FRAGMENTS: tuple[str, ...] = (
    "/login",
    "/logout",
    "/component/contact",
    "/component/users",
    "/component/search",
)

# Política de corpus (v1): não indexar PDFs (eram ~90% dos chunks, texto jurídico
# de baixo valor; o HTML de cada edital já traz o essencial), paginação de listas
# nem componentes Joomla. Religar PDFs é só mudar a flag e recrawlear.
INDEX_PDFS = False
NON_INDEXABLE_PATH_FRAGMENTS: tuple[str, ...] = ("/component/", "/agenda")


def canonical_url(url: str) -> str:
    """Colapsa www.int.unb.br e int.unb.br (mesma página) removendo o 'www.'."""
    return url.replace("://www.", "://", 1)


def is_in_scope(url: str) -> bool:
    """True se a URL deve ser raspada/seguida: host do INT E path em português."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    path = parsed.path or "/"
    return host in ALLOWED_HOSTS and path.startswith(ALLOWED_PATH_PREFIX)


def is_dynamic(url: str) -> bool:
    """True se a URL é de conteúdo que muda com frequência (seleções)."""
    path = urlparse(url).path or ""
    return path.startswith(DYNAMIC_PATH_PREFIXES)


def is_non_content(url: str) -> bool:
    """True para páginas de utilidade do Joomla (login, contato, busca) — pular."""
    path = (urlparse(url).path or "").lower()
    return any(frag in path for frag in NON_CONTENT_PATH_FRAGMENTS)


def is_indexable(url: str, is_pdf: bool) -> bool:
    """True se a página deve entrar no índice (descarta PDFs, ?start= e componentes).

    Pressupõe uma URL já em escopo e não-utilitária.
    """
    if is_pdf and not INDEX_PDFS:
        return False
    parsed = urlparse(url)
    if "start=" in (parsed.query or ""):
        return False
    path = (parsed.path or "").lower()
    return not any(frag in path for frag in NON_INDEXABLE_PATH_FRAGMENTS)
