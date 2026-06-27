"""Extração de texto de PDFs anexados, reusando a normalização do extractor HTML.

Nota: os editais do INT são PDFs escaneados (imagem, sem camada de texto), então
`pypdf` retorna vazio para eles — o pipeline descarta. Este extractor serve aos
PDFs digitais (normas/circulares) e degrada com segurança nos escaneados (OCR é v2).
"""

from __future__ import annotations

import io
from urllib.parse import unquote, urlparse

from pypdf import PdfReader

from src.scraper.config import is_dynamic
from src.scraper.extractor import ExtractedDoc, _normalize_whitespace


def _title_from_url(url: str) -> str:
    """Deriva um título legível do nome do arquivo (ex.: edital-6-2026.pdf)."""
    name = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name.replace("-", " ").replace("_", " ").strip() or url


def extract_pdf(url: str, pdf_bytes: bytes) -> ExtractedDoc:
    """Extrai texto de um PDF (em bytes) usando pypdf."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # PDFs corrompidos/criptografados falham de várias formas
        print(f"[pdf_extractor] falha ao ler {url}: {exc}")
        return ExtractedDoc(url=url, title=_title_from_url(url), text="", is_dynamic=is_dynamic(url))

    text = _normalize_whitespace("\n".join(pages_text))

    # Preferir o título dos metadados; cair para o nome do arquivo.
    meta_title = (reader.metadata.title or "").strip() if reader.metadata else ""
    title = meta_title or _title_from_url(url)

    return ExtractedDoc(url=url, title=title, text=text, is_dynamic=is_dynamic(url))
