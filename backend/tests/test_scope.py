"""Teste da regra mais crítica: o filtro de domínio do crawler.

O crawler só pode seguir links em int.unb.br; qualquer saída para unb.br
(site maior da universidade) é fora de escopo (CONTEXTO_PROJETO.md §2).
"""

from src.scraper.config import is_in_scope


def test_int_urls_in_scope():
    assert is_in_scope("https://int.unb.br/br/institucional/faq")
    assert is_in_scope("https://www.int.unb.br/br/selecoes-int/abertas")


def test_unb_urls_out_of_scope():
    assert not is_in_scope("https://www.unb.br/")
    assert not is_in_scope("https://noticias.unb.br/algo")
    assert not is_in_scope("https://google.com")


def test_other_languages_out_of_scope():
    # Host é do INT, mas só seguimos o português (/br). EN/ES/FR ficam de fora.
    assert not is_in_scope("https://int.unb.br/en/institutional/faq")
    assert not is_in_scope("https://int.unb.br/es/institucional-es/preguntas-frecuentes")
    assert not is_in_scope("https://int.unb.br/fr/")
