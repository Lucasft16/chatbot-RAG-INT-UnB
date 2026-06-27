"""Testes da estratégia de chunking (FAQ semântico vs. janela deslizante)."""

from __future__ import annotations

from src.ingestion.chunker import CHUNK_OVERLAP, CHUNK_SIZE, chunk_document
from src.scraper.extractor import ExtractedDoc


def test_faq_vira_um_unico_chunk_com_pergunta_no_inicio():
    doc = ExtractedDoc(
        url="https://int.unb.br/br/institucional/faq/867-como-funciona",
        title="Como funciona?",
        text="Resposta detalhada do FAQ.",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].text.startswith("Como funciona?")  # pergunta como contexto
    assert chunks[0].id.endswith("#0")
    assert chunks[0].metadata["url"] == doc.url
    assert chunks[0].metadata["is_dynamic"] is False


def test_pagina_longa_usa_janela_deslizante_com_overlap():
    text = "abcdefghij" * 250  # 2500 chars, sem espaços
    doc = ExtractedDoc(url="https://int.unb.br/br/selecoes-int/abertas", title="Abertas",
                       text=text, is_dynamic=True)
    chunks = chunk_document(doc)

    assert len(chunks) >= 3
    assert all(len(c.text) <= CHUNK_SIZE for c in chunks)
    assert [c.id for c in chunks] == [f"{doc.url}#{i}" for i in range(len(chunks))]
    assert all(c.metadata["is_dynamic"] is True for c in chunks)
    # Janelas consecutivas compartilham CHUNK_OVERLAP caracteres.
    assert chunks[0].text[-CHUNK_OVERLAP:] == chunks[1].text[:CHUNK_OVERLAP]


def test_texto_vazio_nao_gera_chunk():
    doc = ExtractedDoc(url="https://int.unb.br/images/edital.pdf", title="Edital", text="   ")
    assert chunk_document(doc) == []


def test_texto_curto_gera_um_chunk():
    doc = ExtractedDoc(url="https://int.unb.br/br/institucional", title="Inst", text="curto")
    assert len(chunk_document(doc)) == 1
