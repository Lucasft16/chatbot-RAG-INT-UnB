"""Testes do generator que não tocam a API (só a limpeza de saída)."""

from __future__ import annotations

from src.rag.generator import _strip_chunk_labels


def test_remove_rotulos_de_trecho_em_colchetes_e_parenteses():
    txt = (
        "As vagas são oferecidas em edital. [Trecho 1]\n"
        "A cotutela é para pós-graduação (Trecho 3, 4).\n"
        "Veja a página [Trecho 2] para mais detalhes."
    )
    out = _strip_chunk_labels(txt)
    assert "Trecho" not in out
    # Sem espaço órfão antes da pontuação.
    assert "edital." in out and "edital ." not in out
    assert "pós-graduação." in out
    assert "página para" in out


def test_remove_rotulo_com_prefixo_fonte():
    # Regressão (D2): "(Fonte: Trecho 1, Trecho 5)" — o rótulo não vem logo após
    # o parêntese, mas ainda deve ser removido.
    txt = "A cotutela é para pós-graduação. (Fonte: Trecho 1, Trecho 5)"
    out = _strip_chunk_labels(txt)
    assert "Trecho" not in out
    assert out.rstrip().endswith("pós-graduação.")


def test_preserva_parentese_legitimo_com_palavra_trecho():
    # "trecho" sem número é prosa legítima, não rótulo — não deve ser apagado.
    txt = "Leia o trecho final do edital antes de se inscrever."
    assert _strip_chunk_labels(txt) == txt


def test_remove_frase_que_narra_o_rotulo_em_prosa():
    # Regressão (A6): "O Trecho 1 também menciona..." — referência em prosa, fora
    # de parênteses. A frase-meta inteira deve sair, preservando o resto.
    txt = (
        "Para revalidar, contate a SAA: (61) 3107-3731.\n"
        "O Trecho 1 também menciona um e-mail, mas o endereço está protegido."
    )
    out = _strip_chunk_labels(txt)
    assert "Trecho" not in out
    assert "Para revalidar, contate a SAA: (61) 3107-3731." in out


def test_preserva_estrutura_markdown_em_lista():
    txt = "Opções:\n*   **A**: primeira\n*   **B**: segunda"
    assert _strip_chunk_labels(txt) == txt


def test_nao_altera_texto_sem_rotulos():
    txt = "O PEC-G é um programa do MEC e do MRE."
    assert _strip_chunk_labels(txt) == txt


def test_preserva_colchetes_que_nao_sao_rotulo():
    txt = "Veja a observação [importante] no edital."
    assert _strip_chunk_labels(txt) == txt
