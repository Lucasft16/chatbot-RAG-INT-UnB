"""Testa o parser do conjunto de avaliação (sem API)."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.run_eval as run_eval
from scripts.run_eval import parse_questions


def test_pega_todas_as_perguntas_reais():
    ids = [q["id"] for q in parse_questions()]

    # Todas as perguntas preenchidas entram (uma+ de cada categoria).
    for qid in ("A1", "A2", "A3", "B1", "B2", "C1", "C2", "D1", "E1"):
        assert qid in ids, f"faltou {qid}"


def test_pula_linhas_modelo(tmp_path: Path):
    md = tmp_path / "q.md"
    md.write_text(
        "## A. Diretas\n\n"
        "| # | Pergunta | Resposta esperada | Status |\n"
        "|---|----------|-------------------|--------|\n"
        "| A1 | Pergunta real? | _(preencher)_ | |\n"
        "| A2 | _(adicionar)_ | | |\n",
        encoding="utf-8",
    )
    ids = [q["id"] for q in parse_questions(md)]
    assert ids == ["A1"]  # linha-modelo (_(adicionar)_) fica de fora


def test_merge_preserva_respostas_e_notas_de_quem_nao_rodou(tmp_path, monkeypatch):
    # Uma rodada parcial não pode apagar respostas/notas de perguntas que não
    # rodaram desta vez (footgun: cota esgota no meio e sobrescreve tudo).
    results_json = tmp_path / "resultados.json"
    monkeypatch.setattr(run_eval, "RESULTS_JSON", results_json)
    prev = [
        {"id": "A1", "question": "q1", "answer": "old1", "sources": [], "status": "✅"},
        {"id": "A2", "question": "q2", "answer": "old2", "sources": [], "status": "⚠️"},
    ]
    results_json.write_text(json.dumps(prev), encoding="utf-8")

    questions = [{"id": "A1"}, {"id": "A2"}]
    new = [{"id": "A1", "question": "q1", "answer": "new1", "sources": []}]  # só A1 rodou
    merged = run_eval._merge_with_existing(new, questions)
    by_id = {m["id"]: m for m in merged}

    assert by_id["A1"]["answer"] == "new1"      # A1 atualizado
    assert by_id["A1"]["status"] == "✅"          # nota preservada
    assert by_id["A2"]["answer"] == "old2"       # A2 NÃO foi apagado
    assert by_id["A2"]["status"] == "⚠️"


def test_estrutura_de_cada_pergunta():
    q = next(q for q in parse_questions() if q["id"] == "A1")
    assert q["question"].startswith("Como funciona")
    assert q["category"].startswith("A.")
    assert "esperada" not in q  # campo é "expected"
    assert "expected" in q
