"""Divisão dos documentos em chunks para indexação.

- FAQ: 1 chunk por página (cada FAQ já é um par pergunta-resposta).
- Demais páginas: janela deslizante de tamanho fixo com overlap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.scraper.extractor import ExtractedDoc

CHUNK_SIZE = 1000       # caracteres (fallback)
CHUNK_OVERLAP = 150     # caracteres


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)  # {url, title, is_dynamic}


def _base_metadata(doc: ExtractedDoc) -> dict:
    # Só tipos aceitos pelo Chroma (str/int/float/bool); nada de None.
    return {"url": doc.url, "title": doc.title, "is_dynamic": doc.is_dynamic}


def _sliding_windows(text: str) -> list[str]:
    """Janela deslizante de CHUNK_SIZE com CHUNK_OVERLAP (fallback)."""
    if len(text) <= CHUNK_SIZE:
        return [text]

    pieces: list[str] = []
    start = 0
    step = CHUNK_SIZE - CHUNK_OVERLAP
    while start < len(text):
        piece = text[start:start + CHUNK_SIZE].strip()
        if piece:
            pieces.append(piece)
        if start + CHUNK_SIZE >= len(text):
            break
        start += step
    return pieces


def chunk_document(doc: ExtractedDoc) -> list[Chunk]:
    """Quebra um documento em chunks conforme a estrutura da página.

    FAQ (`/faq/` na URL) vira 1 chunk com o título (a pergunta) prefixado; demais
    páginas usam janela deslizante. IDs determinísticos (URL + índice) fazem o
    re-scraping dar *upsert* em vez de duplicar.
    """
    text = doc.text.strip()
    if not text:
        # Sem texto útil (ex.: edital escaneado) -> não gera chunk.
        return []

    metadata = _base_metadata(doc)

    if "/faq/" in doc.url:
        body = text if text.startswith(doc.title) else f"{doc.title}\n\n{text}"
        return [Chunk(id=f"{doc.url}#0", text=body, metadata=dict(metadata))]

    return [
        Chunk(id=f"{doc.url}#{i}", text=piece, metadata=dict(metadata))
        for i, piece in enumerate(_sliding_windows(text))
    ]
