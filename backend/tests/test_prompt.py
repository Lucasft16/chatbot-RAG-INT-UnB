"""Testes da montagem do prompt (sem API)."""

from __future__ import annotations

from src.ingestion.vector_store import RetrievedChunk
from src.rag.prompt_templates import CONTACT_URL, SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_tem_contato_e_regras_chave():
    assert CONTACT_URL in SYSTEM_PROMPT
    assert "português" in SYSTEM_PROMPT.lower()
    assert "CONTEXTO" in SYSTEM_PROMPT


def test_system_prompt_proibe_citar_rotulos_de_trecho():
    # Regressão: o LLM vazava rótulos internos ("(Trecho N)") no corpo da resposta.
    assert "Trecho" in SYSTEM_PROMPT
    assert "NUNCA" in SYSTEM_PROMPT


def test_user_prompt_rotula_trechos_pelo_titulo():
    chunks = [
        RetrievedChunk(text="conteúdo A", metadata={"title": "Mobilidade", "url": "u/a"}, score=0.1),
        RetrievedChunk(text="conteúdo B", metadata={"url": "u/b"}, score=0.2),  # sem título -> url
    ]
    prompt = build_user_prompt("Como funciona?", chunks)
    assert "[Trecho 1 — Mobilidade]" in prompt
    assert "[Trecho 2 — u/b]" in prompt
    assert "PERGUNTA:\nComo funciona?" in prompt


def test_user_prompt_sem_contexto():
    prompt = build_user_prompt("Oi?", [])
    assert "nenhum trecho relevante" in prompt
