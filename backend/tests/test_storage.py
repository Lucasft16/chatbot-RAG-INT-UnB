"""Testes do cache de crawl: round-trip, gravação incremental e cache parcial."""

from __future__ import annotations

import pytest

from src.scraper.crawler import CrawledPage


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    """Aponta o cache para um diretório temporário e devolve o módulo."""
    from src.config import settings
    from src.scraper import storage as storage_mod

    monkeypatch.setattr(settings, "raw_data_dir", str(tmp_path))
    return storage_mod


def _pages():
    return [
        CrawledPage(url="https://int.unb.br/br/a", html="<html><body>Página A</body></html>"),
        CrawledPage(url="https://int.unb.br/images/e.pdf", is_pdf=True, pdf_bytes=b"%PDF-1.4 x"),
        CrawledPage(url="https://int.unb.br/br/vazia"),  # sem conteúdo -> não persiste
    ]


def test_round_trip_e_marca_completa(storage):
    assert not storage.has_cache()
    storage.save_pages(_pages())

    assert storage.has_cache()
    assert storage.cache_info() == {"complete": True, "pages": 2}  # a vazia não conta

    loaded = {p.url: p for p in storage.load_pages()}
    assert set(loaded) == {"https://int.unb.br/br/a", "https://int.unb.br/images/e.pdf"}
    assert loaded["https://int.unb.br/images/e.pdf"].pdf_bytes == b"%PDF-1.4 x"
    assert "Página A" in loaded["https://int.unb.br/br/a"].html


def test_gravacao_incremental_sobrevive_a_finalize_parcial(storage):
    # Simula um crawl interrompido: escreve algumas páginas e finaliza como parcial.
    writer = storage.CacheWriter()
    writer.write(_pages()[0])
    writer.finalize(complete=False)

    assert storage.has_cache()
    assert storage.cache_info()["complete"] is False
    assert len(storage.load_pages()) == 1  # a página já gravada foi preservada


def test_load_or_crawl_usa_cache_sem_crawlear(storage, monkeypatch):
    storage.save_pages(_pages())
    # Se tentar crawlear, falha o teste — deve usar o cache.
    monkeypatch.setattr(storage, "crawl", lambda **k: pytest.fail("não deveria crawlear"))
    assert len(storage.load_or_crawl()) == 2
