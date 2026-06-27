"""Pipeline de ingestão: scrape -> extract -> chunk -> embed -> index.

Uso: python -m scripts.run_pipeline [--max-pages N] [--refresh]
Ponto único chamado localmente e pelo GitHub Actions (.github/workflows/rescrape.yml).
"""

from __future__ import annotations

import argparse

from src.ingestion.chunker import chunk_document
from src.ingestion.embeddings import DailyQuotaExceeded, embed_texts
from src.ingestion.vector_store import existing_ids, upsert_chunks
from src.scraper.config import canonical_url, is_indexable
from src.scraper.extractor import extract
from src.scraper.pdf_extractor import extract_pdf
from src.scraper.storage import load_or_crawl

# Indexa em lotes para salvar progresso e poder retomar (cota diária ~1000 não
# cobre o site inteiro de uma vez).
INDEX_BATCH = 100


def run(max_pages: int | None = None, refresh: bool = False) -> None:
    pages = load_or_crawl(max_pages=max_pages, refresh=refresh)
    print(f"[pipeline] {len(pages)} páginas (cache ou crawl)")

    # Filtro de corpus: fora PDFs, paginação e componentes (ver config).
    indexable = [p for p in pages if is_indexable(p.url, p.is_pdf)]

    # Dedup por URL canônica (www.int.unb.br e int.unb.br = mesma página).
    docs = []
    seen: set[str] = set()
    for page in indexable:
        canon = canonical_url(page.url)
        if canon in seen:
            continue
        seen.add(canon)
        if page.is_pdf and page.pdf_bytes is not None:
            docs.append(extract_pdf(canon, page.pdf_bytes))
        elif page.html is not None:
            docs.append(extract(canon, page.html))

    print(f"[pipeline] {len(pages) - len(indexable)} descartadas pelo filtro de corpus, "
          f"{len(indexable) - len(docs)} duplicatas www/sem-www; {len(docs)} páginas a processar")

    all_chunks = [c for doc in docs for c in chunk_document(doc)]
    print(f"[pipeline] {len(all_chunks)} chunks gerados")

    if not all_chunks:
        print("[pipeline] nada a indexar — encerrando")
        return

    # Retoma de onde parou: pula chunks já indexados.
    done = existing_ids()
    todo = [c for c in all_chunks if c.id not in done]
    if done:
        print(f"[pipeline] {len(all_chunks) - len(todo)} chunks já indexados; {len(todo)} a processar")

    indexed = 0
    try:
        for start in range(0, len(todo), INDEX_BATCH):
            batch = todo[start:start + INDEX_BATCH]
            upsert_chunks(batch, embed_texts([c.text for c in batch]))
            indexed += len(batch)
            print(f"[pipeline] indexados {indexed}/{len(todo)}")
    except DailyQuotaExceeded:
        print(
            f"[pipeline] cota DIÁRIA do tier gratuito esgotada. "
            f"Progresso salvo: +{indexed} chunks nesta rodada "
            f"(total na base: {len(done) + indexed}). "
            f"Rode o pipeline de novo amanhã — ele retoma sozinho de onde parou."
        )
        return

    print(f"[pipeline] concluído: +{indexed} chunks (total na base: {len(done) + indexed})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de ingestão RAG do INT/UnB")
    parser.add_argument("--max-pages", type=int, default=None, help="Limite de páginas (dev)")
    parser.add_argument(
        "--refresh", action="store_true",
        help="Força re-coletar o site (ignora o cache em data/raw/).",
    )
    args = parser.parse_args()
    run(max_pages=args.max_pages, refresh=args.refresh)


if __name__ == "__main__":
    main()
