"""Recuperação: pergunta -> embedding -> top-k chunks do vector store.

Dois casos especiais além do top-k semântico:

1. Seleções abertas/encerradas: o top-k é frágil à formulação, então roteamos
   direto para a página-índice da seção (`/selecoes-int/abertas|convencerradas`),
   que já lista tudo.
2. Enumeração genérica ("liste todas as..."): recuperamos um pool maior e
   completamos as páginas dos acertos (uma listagem fatiada perde itens no top-k).
"""

from __future__ import annotations

import re
import unicodedata

from src.config import settings
from src.ingestion.embeddings import embed_query
from src.ingestion.vector_store import (
    RetrievedChunk,
    chunks_by_url,
    chunks_under_path,
    query,
)

# Marcadores de pergunta que pede uma lista (e não um fato pontual).
_ENUM_KEYWORDS = frozenset({"quais", "liste", "listar", "lista", "todas", "todos"})

# Intenção "seleções abertas/encerradas" (categoria E) -> recuperação por seção.
_SELECTION_WORDS = frozenset({"selecao", "selecoes", "edital", "editais", "inscricao", "inscricoes"})
_OPEN_WORDS = frozenset({"aberta", "abertas", "aberto", "abertos", "atualmente", "agora", "vigente", "vigentes", "disponivel", "disponiveis"})
_CLOSED_WORDS = frozenset({"encerrada", "encerradas", "encerrado", "encerrados", "fechada", "fechadas", "passada", "passadas", "anterior", "anteriores", "convencerradas"})

_ABERTAS_PATH = "/selecoes-int/abertas"
_CONVENCERRADAS_PATH = "/selecoes-int/convencerradas"

# Enumeração: pool maior para achar as páginas candidatas e teto de chunks após
# completar as páginas (evita estourar o contexto se muitas páginas casarem).
ENUM_POOL_K = 8
ENUM_MAX_CHUNKS = 15


def _normalize(text: str) -> str:
    """Minúsculas sem acento, para casar palavras de forma robusta."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _tokens(question: str) -> set[str]:
    return set(re.findall(r"\w+", _normalize(question)))


def is_enumeration(question: str) -> bool:
    """Heurística: a pergunta pede uma lista de itens?"""
    return bool(_tokens(question) & _ENUM_KEYWORDS)


def selection_section(question: str) -> str | None:
    """Caminho da seção de seleções, se a pergunta for sobre abertas/encerradas."""
    tokens = _tokens(question)
    if not (tokens & _SELECTION_WORDS):
        return None
    if tokens & _OPEN_WORDS:
        return _ABERTAS_PATH
    if tokens & _CLOSED_WORDS:
        return _CONVENCERRADAS_PATH
    return None


def _complete_pages(pool: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Expande os acertos para as páginas inteiras (chunks irmãos), preservando
    a ordem de relevância das páginas e respeitando o teto de chunks."""
    ordered_urls: list[str] = []
    for c in pool:
        url = c.metadata.get("url")
        if url and url not in ordered_urls:
            ordered_urls.append(url)

    out: list[RetrievedChunk] = []
    for url in ordered_urls:
        for chunk in chunks_by_url(url):
            out.append(chunk)
            if len(out) >= ENUM_MAX_CHUNKS:
                return out
    return out


def _dedup(chunks: list[RetrievedChunk], cap: int) -> list[RetrievedChunk]:
    """Remove repetições (mesma URL + texto), preservando a ordem, até o teto."""
    seen: set[tuple] = set()
    out: list[RetrievedChunk] = []
    for c in chunks:
        key = (c.metadata.get("url"), c.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= cap:
            break
    return out


def retrieve(question: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """Recupera os chunks mais relevantes para a pergunta do usuário."""
    embedding = embed_query(question)

    # Caso 1 (determinístico): seleções abertas/encerradas -> índice da seção
    # primeiro, complementado pelo pool semântico.
    section = selection_section(question)
    if section is not None:
        index_chunks = chunks_under_path(section, limit=ENUM_MAX_CHUNKS)
        pool_k = max(top_k or settings.retrieval_top_k, ENUM_POOL_K)
        semantic = _complete_pages(query(embedding, top_k=pool_k))
        return _dedup(index_chunks + semantic, cap=ENUM_MAX_CHUNKS)

    # Caso 2: enumeração genérica -> completa as páginas dos acertos.
    if is_enumeration(question):
        pool_k = max(top_k or settings.retrieval_top_k, ENUM_POOL_K)
        return _complete_pages(query(embedding, top_k=pool_k))

    # Caso padrão: top-k semântico.
    return query(embedding, top_k=top_k)
