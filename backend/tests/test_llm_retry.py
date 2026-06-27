"""Testes da classificação de rate limit / cota (sem rede, sem sleeps)."""

from __future__ import annotations

import pytest

from src.llm_retry import (
    DailyQuotaExceeded,
    RateLimited,
    call_with_retry,
    is_daily_quota,
    is_rate_limit,
)

PER_MINUTE = "429 RESOURCE_EXHAUSTED ... EmbedContentRequestsPerMinute ... retry in 2s"
PER_DAY = "429 RESOURCE_EXHAUSTED ... EmbedContentRequestsPerDayPerUser ... limit: 1000"


def test_detecta_rate_limit_e_cota_diaria():
    assert is_rate_limit(Exception(PER_MINUTE))
    assert is_rate_limit(Exception(PER_DAY))
    assert is_daily_quota(Exception(PER_DAY))
    assert not is_daily_quota(Exception(PER_MINUTE))


def test_retorna_valor_quando_sucesso():
    assert call_with_retry(lambda: 42, what="t") == 42


def test_cota_diaria_vira_excecao_propria_sem_retry():
    def boom():
        raise Exception(PER_DAY)

    with pytest.raises(DailyQuotaExceeded):
        call_with_retry(boom, what="t")


def test_rate_limit_interativo_falha_rapido():
    # max_retries=1 não dorme: levanta RateLimited na hora.
    def boom():
        raise Exception(PER_MINUTE)

    with pytest.raises(RateLimited):
        call_with_retry(boom, what="t", max_retries=1)


def test_erro_nao_relacionado_a_cota_propaga():
    def boom():
        raise ValueError("erro qualquer")

    with pytest.raises(ValueError):
        call_with_retry(boom, what="t")
