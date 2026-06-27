"""Wrapper fino sobre o ChromaDB (vector store local persistido em `chroma_db/`)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from src.config import settings
from src.ingestion.chunker import Chunk


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict
    score: float  # distância/similaridade retornada pelo Chroma


@lru_cache(maxsize=1)
def get_collection():
    """Abre (ou cria) a coleção persistente do Chroma.

    Fornecemos os embeddings explicitamente no upsert e na query, então a função
    de embedding padrão do Chroma nunca é usada (o provedor fica isolado em
    `ingestion/embeddings.py`).
    """
    import chromadb

    client = chromadb.PersistentClient(path=settings.chroma_db_dir)
    return client.get_or_create_collection(settings.chroma_collection)


def existing_ids() -> set[str]:
    """IDs já na coleção — permite ao pipeline retomar pulando o que já indexou."""
    got = get_collection().get(include=[])
    return set(got.get("ids") or [])


def upsert_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """Insere/atualiza chunks já embeddados na coleção."""
    if not chunks:
        return
    collection = get_collection()
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[c.metadata for c in chunks],
    )


def _chunk_index(chunk_id: str) -> int:
    """IDs são "<url>#<n>"; extrai n para reconstituir a ordem do texto."""
    try:
        return int(chunk_id.rsplit("#", 1)[1])
    except (IndexError, ValueError):
        return 0


def chunks_by_url(url: str) -> list[RetrievedChunk]:
    """Todos os chunks de uma página, na ordem do texto (reconstitui a listagem)."""
    res = get_collection().get(where={"url": url}, include=["documents", "metadatas"])
    ids = res.get("ids") or []
    documents = res.get("documents") or []
    metadatas = res.get("metadatas") or []

    items = sorted(zip(ids, documents, metadatas), key=lambda t: _chunk_index(t[0]))
    return [RetrievedChunk(text=doc, metadata=meta or {}, score=0.0) for _, doc, meta in items]


def chunks_under_path(path_fragment: str, limit: int) -> list[RetrievedChunk]:
    """Chunks das páginas cujo caminho de URL contém `path_fragment`.

    Recuperação determinística por seção (ex.: "/selecoes-int/abertas"), imune à
    formulação da pergunta: a página-índice (caminho == fragmento) vem primeiro e
    já lista tudo; depois as páginas-filhas. Filtra em memória porque o `where` do
    Chroma só faz match exato em metadado.
    """
    res = get_collection().get(include=["documents", "metadatas"])
    ids = res.get("ids") or []
    documents = res.get("documents") or []
    metadatas = res.get("metadatas") or []

    rows = []
    for cid, doc, meta in zip(ids, documents, metadatas):
        path = urlparse((meta or {}).get("url", "")).path
        if path_fragment in path:
            # Página-índice (caminho == fragmento) ordena primeiro; depois por URL.
            is_index = path.rstrip("/").endswith(path_fragment)
            rows.append((not is_index, (meta or {}).get("url", ""), _chunk_index(cid), doc, meta))

    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [RetrievedChunk(text=d, metadata=m or {}, score=0.0) for _, _, _, d, m in rows[:limit]]


def query(embedding: list[float], top_k: int | None = None) -> list[RetrievedChunk]:
    """Busca os top-k chunks mais próximos de um embedding de consulta."""
    top_k = top_k or settings.retrieval_top_k
    collection = get_collection()
    res = collection.query(query_embeddings=[embedding], n_results=top_k)

    # Chroma devolve listas aninhadas por consulta (aqui sempre 1).
    documents = (res.get("documents") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    return [
        RetrievedChunk(text=doc, metadata=meta or {}, score=dist)
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
