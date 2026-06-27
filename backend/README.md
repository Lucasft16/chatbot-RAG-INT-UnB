# chatbot-RAG-INT-UnB

Chatbot RAG em Python/FastAPI que responde perguntas sobre o site institucional do INT/UnB
(mobilidade acadêmica, PEC-G, cotutela, dupla diplomação), com re-scraping automático via
GitHub Actions.

> ⚠️ **Disclaimer**: projeto pessoal/acadêmico de portfólio. **Não é** um canal oficial de
> informação do INT/UnB e não tem qualquer afiliação institucional.

## Arquitetura

```
Site INT (int.unb.br/*) → Scraping (HTML) → Limpeza → Chunking →
Embeddings (Gemini) → Vector Store (ChromaDB) →
[pergunta] → Retrieval (top-k) → Prompt + LLM (Gemini) → Resposta + fontes
```

## Por que RAG (e não fine-tuning)

O conteúdo institucional muda com frequência (seleções abertas/encerradas). RAG permite
atualizar a base continuamente sem re-treinar nada. Fine-tuning de um modelo de embedding
(ex.: BERTimbau) fica como evolução futura (v2).

## Stack

| Camada | Escolha | Por quê |
|--------|---------|---------|
| API | FastAPI | Leve para o caso de uso (vs. Django) |
| Vector store | ChromaDB | Local, persistido, sem serviço externo pago |
| LLM / Embeddings | Google Gemini (`gemini-2.5-flash` / `gemini-embedding-001`) | Tier gratuito, sem cartão. Isolado em `rag/generator.py` e `ingestion/embeddings.py` para troca fácil de provedor (o embedding planejado `text-embedding-004` foi retirado da API; a troca para `gemini-embedding-001` foi só mudar uma variável, validando o isolamento) |
| Scraping | requests + BeautifulSoup + pypdf | Simples e suficiente |

## Estrutura

```
src/
├── scraper/      # crawler, extractor, pdf_extractor, storage (cache do crawl)
├── ingestion/    # chunker, embeddings, vector_store
├── rag/          # retriever, prompt_templates, generator
├── api/          # main.py (FastAPI), routes/chat.py, schemas.py
├── llm_retry.py  # rate limit / cota do Gemini (compartilhado entre embed e geração)
└── config.py
scripts/run_pipeline.py        # orquestra coleta → chunk → embed → index (retomável)
scripts/run_eval.py            # roda o conjunto de avaliação (gera resultados.md/.json)
scripts/analyze_crawl.py       # diagnóstico do crawl (categorias e nº de chunks; sem cota)
data/raw/                      # cache das páginas coletadas (crawl único, gitignored)
tests/eval/                    # conjunto de avaliação (perguntas_teste.md) + resultados
```

> O re-scraping periódico (`.github/workflows/rescrape.yml`) fica na raiz do monorepo.

## Como rodar localmente

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # preencha GEMINI_API_KEY (https://aistudio.google.com/app/apikey)

# (opcional) diagnosticar a coleta sem gastar cota de embedding:
python -m scripts.analyze_crawl

python -m scripts.run_pipeline   # popula o vector store (coleta → chunk → embed → index)
uvicorn src.api.main:app --reload  # API em http://localhost:8000/docs
```

**Notas sobre a ingestão:**

- A **coleta é feita uma vez** e fica em cache em `data/raw/` (gravação incremental, retomável
  se interrompida). As etapas seguintes leem do cache — `run_pipeline` **não re-bate no
  servidor** do INT. Use `--refresh` para forçar nova coleta.
- O tier gratuito do Gemini limita os embeddings a **~100/min e ~1000/dia**. Para sites grandes,
  `run_pipeline` indexa **em lotes**, salva o progresso e **para de forma limpa** ao esgotar a
  cota diária — rode de novo no dia seguinte que ele **retoma de onde parou** (pula o que já foi
  indexado, sem reprocessar nem recolher).

## Resultados da avaliação

Conjunto de perguntas em 5 categorias (diretas, multi-fonte, fora de escopo, armadilhas,
conteúdo dinâmico) em [`tests/eval/perguntas_teste.md`](tests/eval/perguntas_teste.md),
executado de ponta a ponta (retrieve → generate) por
[`scripts/run_eval.py`](scripts/run_eval.py). Cada resposta foi conferida manualmente contra
o HTML coletado em `data/raw/`. Padrão: ✅ correto / ⚠️ parcial / ❌ errado ou alucinado.

**Última rodada (20 perguntas, 5 categorias): 20 ✅ · 0 ❌** — nenhuma alucinação. O conjunto
inclui testes de discriminação fina (ECTS × GPA, ELAP graduação × pós, revalidação × transferência).
Registro completo (respostas + fontes + justificativas) em
[`tests/eval/resultados.md`](tests/eval/resultados.md).

| Categoria | Perguntas | Resultado |
|-----------|:---------:|-----------|
| A. Diretas (uma página) | 8 | ✅✅✅✅✅✅✅✅ |
| B. Multi-fonte | 4 | ✅✅✅✅ |
| C. Fora do escopo (recusa) | 3 | ✅✅✅ |
| D. Armadilhas/ambíguas | 3 | ✅✅✅ |
| E. Conteúdo dinâmico | 2 | ✅✅ |

**O que a avaliação validou:**

- **Discriminação fina (A, B)**: o bot não confunde páginas de nomes parecidos — separa ECTS de
  GPA, recupera as **duas** páginas do ELAP (graduação e pós) e não mistura revalidação de diploma
  com transferência de curso.
- **Recusa e fallback (C, D)**: perguntas fora de escopo (cardápio do RU, previsão do tempo) são
  recusadas com cordialidade; as armadilhas são tratadas admitindo a falta do dado (sem inventar
  prazo médio) e corrigindo premissas erradas (cotutela é só de pós-graduação) — sem alucinação.
- **Conteúdo dinâmico (E)**: o bot usa as seleções **atuais** raspadas do site, validando o re-scraping.

**Melhorias guiadas pela própria avaliação** (cada uma com teste de regressão):

- **Recuperação por seção, determinística (E1)**: "quais seleções estão abertas?" é sensível à
  formulação — uma frase puxava a FAQ de "critérios de seleção" em vez da listagem, e o bot
  respondia que não havia seleções abertas (havia 5). O retriever passou a **rotear a intenção
  abertas/encerradas direto para a página-índice da seção por caminho de URL** (`/selecoes-int/abertas`),
  imune à formulação. **E1 foi de ❌ para ✅**, listando as 5 seleções. Ver `rag/retriever.py`.
- **Recuperação para enumeração**: para perguntas do tipo "liste todas...", o retriever detecta a
  intenção e *completa a página* dos acertos (uma listagem fatiada em vários chunks vinha incompleta).
- **Vazamento de rótulos internos**: o LLM às vezes citava os trechos do contexto na resposta —
  entre parênteses ("(Fonte: Trecho 1)") ou em prosa ("O Trecho 1 menciona..."). Resolvido com
  diretriz no prompt + pós-processamento determinístico no `generator` (garantia final).
  Resultado: 0 ocorrências nas 20 respostas.

Esse é o ciclo de trabalho do projeto: *avaliar → diagnosticar → corrigir → reteste*, com cada
correção fixada por um teste de regressão.

> Reexecutar `python -m scripts.run_eval` após mudanças em chunking/prompt gera comparações
> antes/depois. O script faz *merge* com os resultados anteriores: uma rodada parcial (cota do tier
> gratuito esgota no meio) **não apaga** as respostas/notas das perguntas que não rodaram.

## Limitações conhecidas

- **Rate limits do tier gratuito do Gemini**: ~100 embeddings/min e ~1000/dia (quotas vêm sendo
  reduzidas em 2026). A ingestão trata isso com lotes, retry com backoff e *checkpoint* — retoma
  no dia seguinte sem reprocessar. Sites grandes podem levar alguns dias para indexar por completo.
- O **`chroma_db/` é comitado no repositório** pelo workflow de re-scraping.
- **Privacidade**: tiers gratuitos podem usar prompts para treino. Como o conteúdo é público
  (site institucional), não é bloqueio, mas fica registrado como decisão consciente.
- Responde **somente em português**, ignorando as versões EN/ES/FR do site.
- **Editais em PDF escaneado**: os editais do INT são gerados pelo SEI/UnB como PDF de imagem
  (sem camada de texto), então não são extraídos por leitura de texto. A v1 contorna isso usando
  o conteúdo da página HTML de cada edital (que já traz vagas, benefícios e prazos). **OCR** dos
  PDFs escaneados fica como melhoria de v2.

## Evolução futura (v2)

- **OCR** (ex.: `pytesseract` + `pdf2image`) para ler os editais escaneados na íntegra.
- **Fine-tuning** de um modelo de embedding (ex.: BERTimbau) com pares pergunta-resposta do FAQ,
  comparando qualidade de recuperação antes/depois.
