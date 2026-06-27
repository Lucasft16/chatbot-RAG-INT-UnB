"""Diagnóstico do crawl: o que são as páginas coletadas e quantos chunks geram.

NÃO gasta cota de embedding — só crawl (HTTP) + extração + chunking (CPU).
Serve para decidir o que vale indexar (e o que é ruído) antes de embeddar.

Uso:
    python -m scripts.analyze_crawl                # site inteiro (lento, ~30min)
    python -m scripts.analyze_crawl --max-pages 250  # amostra rápida (~4min)
"""

from __future__ import annotations

import argparse
from collections import Counter
from urllib.parse import urlparse

from src.ingestion.chunker import chunk_document
from src.scraper.extractor import extract
from src.scraper.pdf_extractor import extract_pdf
from src.scraper.storage import load_or_crawl


def categorize(url: str, is_pdf: bool) -> str:
    """Rótulo grosseiro por padrão de URL — onde mora o conteúdo vs. o ruído."""
    path = urlparse(url).path.lower()
    query = urlparse(url).query.lower()

    if is_pdf:
        return "PDF (download/edital)"
    if "start=" in query:
        return "paginação (?start=) — provável duplicata"
    if "/component/phocadownload" in path:
        return "phocadownload (listagem de downloads)"
    if "/component/agenda" in path or "/agenda" in path:
        return "agenda/eventos"
    if "/component/" in path:
        return "component Joomla (outros)"
    if "/selecoes-int/" in path:
        return "seleções (dinâmico, alvo do RAG)"
    if "/institucional/faq/" in path:
        return "FAQ individual (alvo do RAG)"
    if "/institucional/" in path:
        return "institucional"
    if "/estudante-unb/" in path or "/estude-na-unb/" in path:
        return "mobilidade (alvo do RAG)"
    return "outras"


def run(max_pages: int | None = None, refresh: bool = False) -> None:
    pages = load_or_crawl(max_pages=max_pages, refresh=refresh)
    print(f"\n[analyze] {len(pages)} páginas (cache ou crawl)\n")

    by_cat_pages: Counter[str] = Counter()
    by_cat_chunks: Counter[str] = Counter()
    with_query = 0
    empty_text = 0
    total_chunks = 0

    for page in pages:
        cat = categorize(page.url, page.is_pdf)
        by_cat_pages[cat] += 1
        if urlparse(page.url).query:
            with_query += 1

        if page.is_pdf and page.pdf_bytes is not None:
            doc = extract_pdf(page.url, page.pdf_bytes)
        elif page.html is not None:
            doc = extract(page.url, page.html)
        else:
            continue

        if not doc.text.strip():
            empty_text += 1
        n = len(chunk_document(doc))
        by_cat_chunks[cat] += n
        total_chunks += n

    print(f"{'CATEGORIA':<45} {'PÁGINAS':>8} {'CHUNKS':>8}")
    print("-" * 63)
    for cat, npages in by_cat_pages.most_common():
        print(f"{cat:<45} {npages:>8} {by_cat_chunks[cat]:>8}")
    print("-" * 63)
    print(f"{'TOTAL':<45} {len(pages):>8} {total_chunks:>8}\n")

    print(f"[analyze] páginas com query string (?...): {with_query} "
          f"(costumam ser duplicatas/visões dinâmicas)")
    print(f"[analyze] páginas com texto vazio (descartadas no índice): {empty_text}")
    days = (total_chunks + 999) // 1000
    print(f"[analyze] ~{total_chunks} chunks -> ~{days} dia(s) no tier grátis do Gemini (1000/dia)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnóstico do crawl (sem embeddar)")
    parser.add_argument("--max-pages", type=int, default=None, help="Limite de páginas (amostra)")
    parser.add_argument(
        "--refresh", action="store_true",
        help="Força re-coletar o site (ignora o cache em data/raw/).",
    )
    args = parser.parse_args()
    run(max_pages=args.max_pages, refresh=args.refresh)


if __name__ == "__main__":
    main()
