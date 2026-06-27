"""Testes da rota /chat: dedup de fontes e resposta amigável na cota (sem rede)."""

from __future__ import annotations

from src.api.routes import chat as chat_route
from src.api.schemas import ChatRequest
from src.ingestion.vector_store import RetrievedChunk
from src.llm_retry import DailyQuotaExceeded


def _chunk(url: str, title: str = "t") -> RetrievedChunk:
    return RetrievedChunk(text="...", metadata={"url": url, "title": title}, score=0.1)


def test_fontes_sem_duplicatas(monkeypatch):
    chunks = [
        _chunk("https://int.unb.br/br/a"),
        _chunk("https://www.int.unb.br/br/a"),  # par www -> mesma fonte
        _chunk("https://int.unb.br/br/a"),  # mesma URL -> não repete
        _chunk("https://int.unb.br/br/b"),
        RetrievedChunk(text="x", metadata={}, score=0.2),  # sem url -> ignorado
    ]
    monkeypatch.setattr(chat_route, "retrieve", lambda q: chunks)
    monkeypatch.setattr(chat_route, "generate_answer", lambda q, c: "resposta")

    resp = chat_route.chat(ChatRequest(question="oi"))

    assert resp.answer == "resposta"
    # www colapsa para a forma canônica; uma fonte por página.
    assert [s.url for s in resp.sources] == [
        "https://int.unb.br/br/a",
        "https://int.unb.br/br/b",
    ]


def test_cota_estourada_responde_amigavel(monkeypatch):
    def boom(*_):
        raise DailyQuotaExceeded("limite diário")

    monkeypatch.setattr(chat_route, "retrieve", lambda q: [])
    monkeypatch.setattr(chat_route, "generate_answer", boom)

    resp = chat_route.chat(ChatRequest(question="oi"))

    assert resp.answer == chat_route.QUOTA_MESSAGE
    assert resp.sources == []
