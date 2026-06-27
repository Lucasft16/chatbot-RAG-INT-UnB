"""Geração da resposta — ponto único de acoplamento com o LLM.

Isolado aqui para trocar de provedor sem tocar no resto.
Atual: Gemini (gemini-2.5-flash) via SDK `google-genai`.
"""

from __future__ import annotations

import re
from functools import lru_cache

from src.config import settings
from src.ingestion.vector_store import RetrievedChunk
from src.llm_retry import call_with_retry
from src.rag.prompt_templates import SYSTEM_PROMPT, build_user_prompt

# O LLM às vezes vaza os rótulos internos do contexto na resposta, apesar do
# prompt pedir para não citá-los. Removemos como garantia final.
# (1) Entre ()/[] contendo "Trecho N" — exige o dígito para preservar prosa
#     legítima como "(veja o trecho final do edital)".
_CHUNK_LABEL_RE = re.compile(r"\s*[(\[][^)\]]*\btrechos?\s+\d[^)\]]*[)\]]", re.IGNORECASE)
# (2) Em prosa ("O Trecho 1 menciona...") — a frase inteira é descartada.
_BARE_LABEL_RE = re.compile(r"\btrechos?\s+\d", re.IGNORECASE)


def _strip_chunk_labels(text: str) -> str:
    """Remove referências a rótulos de trecho vazadas na resposta.

    Grupos entre ()/[] saem pontualmente; frases que narram o rótulo são
    descartadas inteiras. Processa por linha para preservar o markdown.
    """
    out_lines: list[str] = []
    for line in text.split("\n"):
        line = _CHUNK_LABEL_RE.sub("", line)
        if _BARE_LABEL_RE.search(line):
            sentences = re.split(r"(?<=[.!?])\s+", line)
            line = " ".join(s for s in sentences if not _BARE_LABEL_RE.search(s))
        out_lines.append(line)

    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r" +([.,;:!?])", r"\1", cleaned)        # espaço órfão antes de pontuação
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)             # colapsa linhas em branco extras
    return cleaned.strip()


@lru_cache(maxsize=1)
def _client():
    # Import/criação preguiçosos: importar o módulo não deve exigir a chave.
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


def generate_answer(
    question: str, chunks: list[RetrievedChunk], *, max_retries: int = 1
) -> str:
    """Gera a resposta final a partir da pergunta e dos chunks recuperados.

    Levanta LLMQuotaError em caso de limite de cota (tratado pela API).
    `max_retries=1` (padrão, caminho interativo) falha rápido no limite por minuto;
    jobs em lote (`run_eval`) passam um valor maior para esperar e continuar.
    """
    user_prompt = build_user_prompt(question, chunks)

    def _call() -> str:
        response = _client().models.generate_content(
            model=settings.gemini_generation_model,
            contents=user_prompt,
            config={"system_instruction": SYSTEM_PROMPT},
        )
        return _strip_chunk_labels((response.text or "").strip())

    return call_with_retry(_call, what="generator", max_retries=max_retries)
