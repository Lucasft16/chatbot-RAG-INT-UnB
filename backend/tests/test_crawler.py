"""Testes das regras de URL do crawler: normalização e o que seguir.

Cobre decisões tomadas a partir do site real: forçar HTTPS (links http:// do
phocadownload davam Connection refused), pular utilidades do Joomla (login,
contato) e seguir PDFs do host do INT mesmo fora de /br.
"""

from __future__ import annotations

from src.scraper.config import canonical_url, is_indexable, is_non_content
from src.scraper.crawler import _normalize, _should_follow


def test_normalize_forca_https_canonicaliza_www_remove_fragmento_e_barra():
    assert _normalize("http://int.unb.br/br/x") == "https://int.unb.br/br/x"
    assert _normalize("https://int.unb.br/br/x/") == "https://int.unb.br/br/x"
    assert _normalize("https://int.unb.br/br/x#secao") == "https://int.unb.br/br/x"
    # www -> sem www (mesma página)
    assert _normalize("https://www.int.unb.br/br/x") == "https://int.unb.br/br/x"
    # http + www + barra + fragmento, tudo de uma vez
    assert _normalize("http://www.int.unb.br/br/x/#a") == "https://int.unb.br/br/x"


def test_canonical_url_colapsa_www():
    assert canonical_url("https://www.int.unb.br/br/x") == "https://int.unb.br/br/x"
    assert canonical_url("https://int.unb.br/br/x") == "https://int.unb.br/br/x"


def test_is_non_content_pula_utilidades_do_joomla():
    assert is_non_content("https://int.unb.br/br/institucional/login?view=reset")
    assert is_non_content("https://int.unb.br/br/component/contact/contact/177-x/398")
    # conteúdo de verdade não é "non-content"
    assert not is_non_content("https://int.unb.br/br/institucional/faleconosco")
    assert not is_non_content("https://int.unb.br/br/estudante-unb/a-mobilidade-academica")


def test_should_follow_padrao_nao_segue_pdfs():
    # conteúdo em escopo
    assert _should_follow("https://int.unb.br/br/institucional/faq")
    # utilidade do Joomla -> não segue
    assert not _should_follow("https://int.unb.br/br/institucional/login?view=reset")
    # v1 não indexa PDFs (INDEX_PDFS=False) -> não vale baixá-los
    assert not _should_follow("https://int.unb.br/images/edital-6-2026.pdf")
    # página HTML fora de escopo -> não segue
    assert not _should_follow("https://unb.br/br/qualquer")


def test_should_follow_pdf_quando_index_pdfs_ligado(monkeypatch):
    import src.scraper.crawler as crawler

    monkeypatch.setattr(crawler, "INDEX_PDFS", True)
    # Com a flag ligada, PDF do host do INT volta a ser seguido (mesmo fora de /br).
    assert crawler._should_follow("https://int.unb.br/images/edital-6-2026.pdf")
    assert not crawler._should_follow("https://unb.br/algo/edital.pdf")  # host de fora


def test_is_indexable_filtra_pdf_paginacao_e_componentes():
    # HTML de conteúdo -> indexa
    assert is_indexable("https://int.unb.br/br/selecoes-int/abertas", is_pdf=False)
    assert is_indexable("https://int.unb.br/br/institucional/faq/867-x", is_pdf=False)
    # PDF -> fora do corpus v1
    assert not is_indexable("https://int.unb.br/images/edital.pdf", is_pdf=True)
    # paginação de lista -> duplicata, fora
    assert not is_indexable("https://int.unb.br/br/selecoes-int/abertas?start=20", is_pdf=False)
    # componentes Joomla (phocadownload, agenda) -> fora
    assert not is_indexable("https://int.unb.br/br/component/phocadownload/category/1", is_pdf=False)
    assert not is_indexable("https://int.unb.br/br/component/agenda/agendas?x=1", is_pdf=False)
