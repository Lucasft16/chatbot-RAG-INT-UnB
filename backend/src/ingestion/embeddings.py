"""Geração de embeddings — ponto único de acoplamento com o provedor de embeddings.

Isolado aqui para trocar de provedor sem tocar no resto do pipeline.
Atual: Gemini (gemini-embedding-001) via SDK `google-genai`.
"""

from __future__ import annotations

from functools import lru_cache

from src.config import settings
# Re-exporta DailyQuotaExceeded para quem importa daqui (ex.: run_pipeline).
from src.llm_retry import DailyQuotaExceeded, call_with_retry  # noqa: F401

# task_type distinto melhora o retrieval: documentos indexados vs. consulta.
TASK_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_QUERY = "RETRIEVAL_QUERY"

# Lotes pequenos suavizam o ritmo contra a cota por minuto (~100/min) do tier grátis.
BATCH_SIZE = 20


@lru_cache(maxsize=1)
def _client():
    # Import/criação preguiçosos: importar o módulo não deve exigir a chave.
    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


def _embed_batch(batch: list[str], task_type: str) -> list[list[float]]:
    def _call() -> list[list[float]]:
        response = _client().models.embed_content(
            model=settings.gemini_embedding_model,
            contents=batch,
            config={"task_type": task_type},
        )
        return [embedding.values for embedding in response.embeddings]

    # Ingestão em lote: pode esperar a janela do minuto resetar (política padrão).
    return call_with_retry(_call, what="embeddings")


def embed_texts(texts: list[str], task_type: str = TASK_DOCUMENT) -> list[list[float]]:
    """Retorna um vetor de embedding para cada texto.

    Use TASK_DOCUMENT ao indexar chunks e TASK_QUERY ao embeddar a pergunta.
    Faz lotes e re-tenta com backoff ao bater no rate limit do tier gratuito.
    """
    if not texts:
        return []

    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start:start + BATCH_SIZE], task_type))
    return vectors


def embed_query(text: str) -> list[float]:
    """Atalho para embeddar uma única pergunta do usuário."""
    return embed_texts([text], task_type=TASK_QUERY)[0]
