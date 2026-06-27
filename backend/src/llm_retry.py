"""Tratamento de rate limit / cota do Gemini (compartilhado por embeddings e geração).

Distingue limite POR MINUTO (re-tenta com backoff) de cota DIÁRIA (não adianta
re-tentar). Ambas herdam de LLMQuotaError, então a API trata as duas num só
`except` e responde com gentileza em vez de estourar 500.
"""

from __future__ import annotations

import re
import time
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")

# Política padrão (ingestão em lote): pode esperar a janela do minuto resetar.
MAX_RETRIES = 6
BACKOFF_SECONDS: Sequence[float] = (5, 15, 30, 45, 60, 60)


class LLMQuotaError(RuntimeError):
    """Base para limites de uso do provedor de LLM (tratado como temporário)."""


class DailyQuotaExceeded(LLMQuotaError):
    """Cota diária do tier gratuito esgotada — só reseta no dia seguinte."""


class RateLimited(LLMQuotaError):
    """Limite por minuto persistente após esgotar as re-tentativas."""


def is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)


def is_daily_quota(exc: Exception) -> bool:
    return "PerDay" in str(exc) or "RequestsPerDay" in str(exc)


def _retry_delay(exc: Exception, attempt: int, backoff: Sequence[float]) -> float:
    """Usa o retryDelay sugerido pela API, se houver; senão o backoff fixo."""
    fallback = backoff[min(attempt, len(backoff) - 1)]
    match = re.search(r"retry in ([\d.]+)s", str(exc))
    return max(float(match.group(1)), fallback) if match else fallback


def call_with_retry(
    fn: Callable[[], T],
    *,
    what: str,
    max_retries: int = MAX_RETRIES,
    backoff: Sequence[float] = BACKOFF_SECONDS,
) -> T:
    """Executa `fn()` tratando rate limit do Gemini.

    - cota diária -> DailyQuotaExceeded (sem re-tentar);
    - limite por minuto -> re-tenta com backoff; persistindo, RateLimited;
    - erros não relacionados a cota -> propagados como estão.

    Use `max_retries=1` no caminho interativo (API) para falhar rápido em vez de
    segurar a requisição por minutos.
    """
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — re-classificamos abaixo
            if is_daily_quota(exc):
                raise DailyQuotaExceeded(str(exc)) from exc
            if is_rate_limit(exc):
                if attempt < max_retries - 1:
                    delay = _retry_delay(exc, attempt, backoff)
                    print(f"[{what}] rate limit por minuto; aguardando {delay:.0f}s e tentando de novo…")
                    time.sleep(delay)
                    continue
                raise RateLimited(str(exc)) from exc
            raise
    raise RuntimeError(f"{what}: estado inesperado no retry (max_retries={max_retries})")
