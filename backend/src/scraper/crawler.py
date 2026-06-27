"""Crawler do site do INT: BFS a partir de `SEED_URLS`, seguindo links em escopo.

Coleta HTML e detecta PDFs anexados (delegados ao `pdf_extractor`). Links são
normalizados (sem fragmento/barra final) para deduplicar.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.scraper.config import (
    ALLOWED_HOSTS,
    INDEX_PDFS,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SEED_URLS,
    USER_AGENT,
    canonical_url,
    is_in_scope,
    is_non_content,
)

# Timeouts no int.unb.br são frequentes e transitórios; vale uma 2ª tentativa.
MAX_FETCH_ATTEMPTS = 2


@dataclass
class CrawledPage:
    url: str
    html: str | None = None
    is_pdf: bool = False
    pdf_bytes: bytes | None = None
    discovered_links: list[str] = field(default_factory=list)


def _normalize(url: str) -> str:
    """Remove fragmento/barra final, força HTTPS e colapsa www. para deduplicar.

    Alguns links vêm com `http://`, mas o servidor recusa a porta 80; promover
    para `https://` recupera esses PDFs e colapsa http/https numa URL só.
    """
    url, _ = urldefrag(url)
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    url = canonical_url(url)
    if url.endswith("/") and len(urlparse(url).path) > 1:
        url = url[:-1]
    return url


def _is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _should_follow(url: str) -> bool:
    """Decide se um link descoberto deve entrar na fila."""
    if is_non_content(url):
        return False
    if _is_pdf_url(url) and not INDEX_PDFS:
        return False
    if is_in_scope(url):
        return True
    # PDFs anexados (editais) podem morar fora de /br, mas só no host do INT.
    host = urlparse(url).hostname or ""
    return host in ALLOWED_HOSTS and _is_pdf_url(url)


def _fetch(session: requests.Session, url: str):
    """GET com uma re-tentativa em timeout. Mantém o delay de boa cidadania."""
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            return session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.Timeout:
            label = "tentando de novo" if attempt < MAX_FETCH_ATTEMPTS else "desisti"
            print(f"[crawler] timeout em {url} (tentativa {attempt}; {label})")
        except requests.RequestException as exc:
            print(f"[crawler] falha em {url}: {exc}")
            return None
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)
    return None


def _extract_links(base_url: str, html: str) -> list[str]:
    """Resolve e normaliza os links seguíveis de uma página."""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = _normalize(urljoin(base_url, href))
        if _should_follow(absolute):
            links.append(absolute)
    return links


def crawl(
    seed_urls: list[str] | None = None,
    max_pages: int | None = None,
    on_page: Callable[[CrawledPage], None] | None = None,
) -> list[CrawledPage]:
    """Percorre o site do INT e retorna as páginas em escopo.

    Args:
        seed_urls: pontos de partida; usa scraper.config.SEED_URLS se None.
        max_pages: limite de páginas (útil em testes/dev); None = sem limite.
        on_page: callback por página — permite gravação incremental do cache.
    """
    from collections import deque

    queue: deque[str] = deque(_normalize(u) for u in (seed_urls or SEED_URLS))
    visited: set[str] = set()
    pages: list[CrawledPage] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while queue and (max_pages is None or len(pages) < max_pages):
        url = queue.popleft()
        if url in visited or not _should_follow(url):
            continue
        visited.add(url)

        resp = _fetch(session, url)
        if resp is None:
            continue

        if resp.status_code != 200:
            print(f"[crawler] {resp.status_code} em {url}")
            continue

        content_type = resp.headers.get("content-type", "")
        is_pdf = "application/pdf" in content_type or _is_pdf_url(url)

        if is_pdf:
            page = CrawledPage(url=url, is_pdf=True, pdf_bytes=resp.content)
            pages.append(page)
            if on_page is not None:
                on_page(page)
            continue

        # Só HTML vira conteúdo: feeds RSS/Atom e outros XML do Joomla passam no
        # escopo mas não são úteis — ignoramos.
        if "html" not in content_type.lower():
            print(f"[crawler] ignorando não-HTML ({content_type or 'sem content-type'}) em {url}")
            continue

        html = resp.text
        links = _extract_links(url, html)
        page = CrawledPage(url=url, html=html, discovered_links=links)
        pages.append(page)
        if on_page is not None:
            on_page(page)

        for link in links:
            if link not in visited:
                queue.append(link)

    print(f"[crawler] visitadas {len(visited)} URLs, coletadas {len(pages)} páginas")
    return pages
