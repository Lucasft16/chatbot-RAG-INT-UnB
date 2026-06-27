"""Rota do chat: orquestra retrieval -> geração."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.schemas import ChatRequest, ChatResponse, Source
from src.ingestion.vector_store import RetrievedChunk
from src.llm_retry import LLMQuotaError
from src.rag.generator import generate_answer
from src.rag.retriever import retrieve
from src.scraper.config import canonical_url

router = APIRouter(prefix="/chat", tags=["chat"])

# Mensagem amigável quando a API gratuita está sem cota — melhor que um 500 cru.
QUOTA_MESSAGE = (
    "Estou temporariamente sem capacidade para responder agora "
    "(limite da API gratuita). Tente novamente em alguns minutos."
)


def _unique_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    """Fontes sem repetição: vários chunks (e o par www/sem-www) viram uma só."""
    sources: list[Source] = []
    seen: set[str] = set()
    for c in chunks:
        url = c.metadata.get("url")
        if not url:
            continue
        canon = canonical_url(url)  # int.unb.br e www.int.unb.br = mesma fonte
        if canon not in seen:
            seen.add(canon)
            sources.append(Source(url=canon, title=c.metadata.get("title")))
    return sources


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        chunks = retrieve(req.question)
        answer = generate_answer(req.question, chunks)
    except LLMQuotaError:
        # Cota (diária ou por minuto) estourada: responde com gentileza, sem 500.
        return ChatResponse(answer=QUOTA_MESSAGE, sources=[])

    return ChatResponse(answer=answer, sources=_unique_sources(chunks))
