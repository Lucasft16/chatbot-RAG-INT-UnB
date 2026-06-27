"""Extração e limpeza de texto do HTML bruto (Joomla do int.unb.br).

Remove menus/rodapé/navegação e pega só o conteúdo útil. O título vem do <title>
("INT - UnB - <título>"); o conteúdo, do primeiro de CONTENT_SELECTORS.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from src.scraper.config import is_dynamic

# Seletores de conteúdo, em ordem de preferência (1º que existir e tiver texto vence).
CONTENT_SELECTORS = ("[itemprop=articleBody]", ".item-page", "#content", "main")

# Elementos de ruído a remover antes de extrair o texto.
NOISE_SELECTORS = (
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    ".breadcrumb",
    ".breadcrumbs",
    ".pagenav",
)

# Prefixo padrão do <title> do site.
TITLE_PREFIX = "INT - UnB - "

# Linha de breadcrumb que sobra como texto mesmo sem classe (.breadcrumb).
_BREADCRUMB_RE = re.compile(r"^\s*Você está aqui:.*$", re.MULTILINE)


@dataclass
class ExtractedDoc:
    url: str
    title: str
    text: str
    is_dynamic: bool = False  # conteúdo que muda com frequência (seleções)


def _clean_title(soup: BeautifulSoup) -> str:
    if not soup.title or not soup.title.string:
        return ""
    title = soup.title.string.strip()
    if title.startswith(TITLE_PREFIX):
        title = title[len(TITLE_PREFIX):].strip()
    return title


def _normalize_whitespace(text: str) -> str:
    text = _BREADCRUMB_RE.sub("", text)
    # Colapsa espaços/tabs e remove linhas em branco repetidas.
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def extract(url: str, html: str) -> ExtractedDoc:
    """Extrai título + texto limpo de uma página HTML do INT."""
    soup = BeautifulSoup(html, "lxml")
    title = _clean_title(soup)

    # Primeiro container com conteúdo de verdade.
    container = None
    for selector in CONTENT_SELECTORS:
        candidate = soup.select_one(selector)
        if candidate and candidate.get_text(strip=True):
            container = candidate
            break

    text = ""
    if container is not None:
        for noise in container.select(",".join(NOISE_SELECTORS)):
            noise.decompose()
        text = _normalize_whitespace(container.get_text("\n"))

    return ExtractedDoc(url=url, title=title, text=text, is_dynamic=is_dynamic(url))
