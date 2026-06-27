"""Testes da lógica de recuperação (enumeração e seções de seleção), sem API/Chroma."""

from __future__ import annotations

import src.rag.retriever as retriever
from src.ingestion.vector_store import RetrievedChunk
from src.rag.retriever import _complete_pages, is_enumeration, selection_section


def test_is_enumeration_detecta_perguntas_de_lista():
    assert is_enumeration("Quais seleções estão abertas agora?")
    assert is_enumeration("Liste todas as formas de estudar no exterior")
    assert is_enumeration("Todos os editais abertos")


def test_is_enumeration_ignora_perguntas_pontuais():
    assert not is_enumeration("Qual a diferença entre cotutela e dupla diplomação?")
    assert not is_enumeration("Quando abre o vestibular da UnB?")
    assert not is_enumeration("O que é o PEC-G?")


def test_selection_section_roteia_abertas_e_encerradas():
    # Várias formulações (incl. a que regrediu o E1) devem cair em /abertas.
    assert selection_section("Quais seleções estão abertas no INT atualmente?") == "/selecoes-int/abertas"
    assert selection_section("Tem algum edital com inscrições abertas?") == "/selecoes-int/abertas"
    # Encerradas/passadas -> /convencerradas.
    assert selection_section(
        "Existe alguma seleção com inscrições encerradas recentemente?"
    ) == "/selecoes-int/convencerradas"


def test_selection_section_none_quando_nao_e_sobre_selecoes():
    assert selection_section("O que é o PEC-G?") is None
    assert selection_section("Quais as formas de estudar no exterior?") is None  # sem termo de seleção


def _chunk(url: str, idx: int) -> RetrievedChunk:
    return RetrievedChunk(text=f"t{idx}", metadata={"url": url}, score=0.1 * idx)


def test_retrieve_secao_usa_indice_deterministico(monkeypatch):
    # Mesmo que o pool semântico erre (puxe a FAQ de critérios), o índice da
    # seção entra primeiro e completo.
    index_chunks = [_chunk("/abertas", 0), _chunk("/abertas", 1)]
    monkeypatch.setattr(retriever, "embed_query", lambda q: [0.0])
    monkeypatch.setattr(retriever, "chunks_under_path", lambda path, limit: index_chunks)
    monkeypatch.setattr(retriever, "query", lambda emb, top_k: [_chunk("/faq-criterios", 0)])
    monkeypatch.setattr(retriever, "chunks_by_url", lambda url: [_chunk(url, 0)])

    out = retriever.retrieve("Quais seleções estão abertas no INT atualmente?")
    urls = [c.metadata["url"] for c in out]
    assert urls[:2] == ["/abertas", "/abertas"]  # índice primeiro e completo
    assert "/faq-criterios" in urls               # pool semântico complementa


def test_complete_pages_traz_chunks_irmaos_da_pagina(monkeypatch):
    pages = {
        "/abertas": [_chunk("/abertas", 0), _chunk("/abertas", 1)],
        "/edital-x": [_chunk("/edital-x", 0)],
    }
    monkeypatch.setattr(retriever, "chunks_by_url", lambda url: pages[url])
    out = _complete_pages([_chunk("/abertas", 0), _chunk("/edital-x", 0)])
    assert [c.text for c in out] == ["t0", "t1", "t0"]


def test_complete_pages_respeita_o_teto(monkeypatch):
    big = [_chunk("/p", i) for i in range(50)]
    monkeypatch.setattr(retriever, "chunks_by_url", lambda url: big)
    out = _complete_pages([_chunk("/p", 0)])
    assert len(out) == retriever.ENUM_MAX_CHUNKS
