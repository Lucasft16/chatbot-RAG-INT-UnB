"""Cache em disco das páginas coletadas — crawlear o site do INT uma vez só.

Evita re-bater no servidor e permite re-chunkar/re-embeddar offline. A gravação é
incremental (um crawl interrompido preserva o que já baixou) e `meta.json` marca
se a última coleta foi completa.

Layout em `data/raw/`:
  - manifest.jsonl  -> uma linha {url, is_pdf, file} por página
  - meta.json       -> {complete: bool, pages: int}
  - pages/<hash>.html | <hash>.pdf

Coletas parciais por `--max-pages` não são persistidas (uma amostra nunca deve
ser confundida com o site inteiro).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from src.config import settings
from src.scraper.crawler import CrawledPage, crawl

MANIFEST_NAME = "manifest.jsonl"
META_NAME = "meta.json"
PAGES_SUBDIR = "pages"


def _raw_dir() -> Path:
    return Path(settings.raw_data_dir)


def _page_filename(url: str, is_pdf: bool) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}.{'pdf' if is_pdf else 'html'}"


def has_cache() -> bool:
    return (_raw_dir() / MANIFEST_NAME).exists()


def cache_info() -> dict:
    """{complete, pages} da última coleta, ou complete=None se não houver meta."""
    meta = _raw_dir() / META_NAME
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    return {"complete": None, "pages": None}


class CacheWriter:
    """Grava páginas no cache uma a uma (incremental), limpando a coleta anterior."""

    def __init__(self) -> None:
        self.raw = _raw_dir()
        self.pages_dir = self.raw / PAGES_SUBDIR
        shutil.rmtree(self.pages_dir, ignore_errors=True)  # descarta coleta antiga
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        (self.raw / META_NAME).unlink(missing_ok=True)  # inválido até finalizar
        self._manifest = (self.raw / MANIFEST_NAME).open("w", encoding="utf-8")
        self.count = 0

    def write(self, page: CrawledPage) -> None:
        fname = _page_filename(page.url, page.is_pdf)
        target = self.pages_dir / fname
        if page.is_pdf and page.pdf_bytes is not None:
            target.write_bytes(page.pdf_bytes)
        elif page.html is not None:
            target.write_text(page.html, encoding="utf-8")
        else:
            return  # página sem conteúdo — não persiste
        self._manifest.write(json.dumps({"url": page.url, "is_pdf": page.is_pdf, "file": fname}) + "\n")
        self._manifest.flush()  # durável: sobrevive a um Ctrl+C
        self.count += 1

    def finalize(self, complete: bool) -> None:
        self._manifest.close()
        (self.raw / META_NAME).write_text(
            json.dumps({"complete": complete, "pages": self.count}), encoding="utf-8"
        )


def save_pages(pages: list[CrawledPage]) -> None:
    """Grava uma lista de páginas no cache de uma vez (marca como completa)."""
    writer = CacheWriter()
    for page in pages:
        writer.write(page)
    writer.finalize(complete=True)
    print(f"[storage] {writer.count} páginas salvas em {writer.raw}/")


def load_pages() -> list[CrawledPage]:
    """Carrega as páginas do cache em disco."""
    raw = _raw_dir()
    pages_dir = raw / PAGES_SUBDIR
    pages: list[CrawledPage] = []
    with (raw / MANIFEST_NAME).open(encoding="utf-8") as manifest:
        for line in manifest:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            target = pages_dir / rec["file"]
            if rec["is_pdf"]:
                pages.append(CrawledPage(url=rec["url"], is_pdf=True, pdf_bytes=target.read_bytes()))
            else:
                pages.append(CrawledPage(url=rec["url"], html=target.read_text(encoding="utf-8")))
    print(f"[storage] {len(pages)} páginas carregadas do cache ({raw}/)")
    return pages


def load_or_crawl(max_pages: int | None = None, refresh: bool = False) -> list[CrawledPage]:
    """Reusa o cache se existir; senão crawleia (persistindo de forma incremental).

    `refresh=True` força recoletar; `max_pages` faz coleta parcial não persistida.
    """
    if not refresh and has_cache():
        if cache_info().get("complete") is False:
            print("[storage] AVISO: cache PARCIAL (último crawl interrompido). "
                  "Use --refresh para recoletar o site inteiro.")
        return load_pages()

    if max_pages is not None:
        pages = crawl(max_pages=max_pages)
        print(f"[storage] coleta parcial (max_pages={max_pages}) — não persistida no cache")
        return pages

    # Coleta completa: persiste página a página; complete=True só se terminar bem.
    writer = CacheWriter()
    completed = False
    try:
        pages = crawl(on_page=writer.write)
        completed = True
        return pages
    finally:
        writer.finalize(complete=completed)
        status = "completo" if completed else "PARCIAL (interrompido — use --refresh depois)"
        print(f"[storage] cache {status}: {writer.count} páginas em {writer.raw}/")
