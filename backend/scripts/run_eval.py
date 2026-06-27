"""Avaliador: roda o conjunto `tests/eval/perguntas_teste.md` pela pipeline RAG.

Executa cada pergunta in-process (mesmo caminho da API: retrieve -> generate) e
grava `resultados.md` (tabela p/ notas ✅/⚠️/❌) + `resultados.json` (registro).
Requer GEMINI_API_KEY e o vector store já populado (`scripts/run_pipeline`).

Uso: python -m scripts.run_eval
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent / "tests" / "eval"
QUESTIONS_MD = EVAL_DIR / "perguntas_teste.md"
RESULTS_MD = EVAL_DIR / "resultados.md"
RESULTS_JSON = EVAL_DIR / "resultados.json"

# Marcadores de linha que ainda não viraram pergunta de verdade.
_PLACEHOLDERS = ("_(adicionar)_", "_(preencher)_")


def parse_questions(md_path: Path = QUESTIONS_MD) -> list[dict]:
    """Extrai {id, category, question, expected} das tabelas do markdown."""
    questions: list[dict] = []
    category = ""
    for raw in md_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()

        header = re.match(r"^##\s+([A-E])\.\s+(.*)", line)
        if header:
            category = f"{header.group(1)}. {header.group(2)}".strip()
            continue

        if not line.startswith("|"):
            continue

        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 2:
            continue
        qid, question = cols[0], cols[1]

        # Pula cabeçalho da tabela e a linha separadora (|---|---|).
        if qid in ("#", "") or set(qid) <= set("-: "):
            continue
        # Pula linhas-modelo ainda não preenchidas.
        if not question or question.startswith("_(") or any(p in question for p in _PLACEHOLDERS):
            continue

        questions.append({
            "id": qid,
            "category": category,
            "question": question,
            "expected": cols[2] if len(cols) > 2 else "",
        })
    return questions


def _one_line(text: str, limit: int = 200) -> str:
    """Achata a resposta para caber numa célula de tabela markdown."""
    flat = re.sub(r"\s+", " ", text.replace("|", "\\|")).strip()
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _unique_urls(chunks) -> list[str]:
    seen: list[str] = []
    for c in chunks:
        url = c.metadata.get("url")
        if url and url not in seen:
            seen.append(url)
    return seen


def run() -> None:
    # Imports do caminho RAG aqui para `import scripts.run_eval` não exigir chave.
    from src.llm_retry import MAX_RETRIES, DailyQuotaExceeded, LLMQuotaError
    from src.rag.generator import generate_answer
    from src.rag.retriever import retrieve

    questions = parse_questions()
    print(f"[eval] {len(questions)} perguntas carregadas de {QUESTIONS_MD.name}")

    results: list[dict] = []
    for q in questions:
        try:
            chunks = retrieve(q["question"])
            # Lote: espera a janela do minuto e continua (vs. falhar rápido na API).
            answer = generate_answer(q["question"], chunks, max_retries=MAX_RETRIES)
        except DailyQuotaExceeded:
            print(f"[eval] cota DIÁRIA esgotada em {q['id']} — esperar não adianta; "
                  f"parando (resultados parciais salvos).")
            break
        except LLMQuotaError:
            print(f"[eval] limite por minuto persistente em {q['id']} mesmo após "
                  f"retries — parando (resultados parciais salvos).")
            break

        urls = _unique_urls(chunks)
        results.append({**q, "answer": answer, "sources": urls})
        print(f"[eval] {q['id']}: {q['question'][:55]}… -> {answer[:70]}…")

    merged = _merge_with_existing(results, questions)
    _write_outputs(merged)
    print(f"[eval] {len(results)} respostas novas; {len(merged)} no total "
          f"salvas em {RESULTS_MD.name} e {RESULTS_JSON.name}")


def _merge_with_existing(new_results: list[dict], questions: list[dict]) -> list[dict]:
    """Funde as respostas novas com as já salvas, na ordem do conjunto.

    Evita que uma rodada parcial (cota esgota no meio) apague respostas/notas das
    perguntas que não rodaram. Mantém só os IDs do conjunto atual e preserva
    `status`/`avaliacao` (notas) já gravados.
    """
    by_id: dict[str, dict] = {}
    if RESULTS_JSON.exists():
        try:
            for entry in json.loads(RESULTS_JSON.read_text(encoding="utf-8")):
                by_id[entry["id"]] = entry
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # arquivo ausente/corrompido: começa do zero
    for r in new_results:
        # Resposta nova substitui a antiga, mas mantém status/avaliacao se havia.
        prev = by_id.get(r["id"], {})
        by_id[r["id"]] = {**{k: prev[k] for k in ("status", "avaliacao") if k in prev}, **r}
    return [by_id[q["id"]] for q in questions if q["id"] in by_id]


def _write_outputs(results: list[dict]) -> None:
    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Resultados da avaliação — {date.today().isoformat()}",
        "",
        "> Gerado por `scripts/run_eval.py`. Coluna **Status** (nota manual):",
        "> ✅ correto / ⚠️ parcial / ❌ errado ou alucinado.",
        "",
        "| # | Categoria | Pergunta | Resposta | Fontes | Status |",
        "|---|-----------|----------|----------|--------|--------|",
    ]
    for r in results:
        srcs = "<br>".join(r["sources"][:3]) or "—"
        lines.append(
            f"| {r['id']} | {r['category']} | {_one_line(r['question'], 80)} "
            f"| {_one_line(r['answer'])} | {srcs} | {r.get('status', '')} |"
        )
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
