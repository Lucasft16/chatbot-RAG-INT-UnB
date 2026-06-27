# chatbot-RAG-INT-UnB

Chatbot RAG que responde perguntas sobre o site institucional do INT/UnB (mobilidade
acadêmica, PEC-G, cotutela, dupla diplomação), com re-scraping automático via GitHub Actions.

> ⚠️ **Disclaimer**: projeto pessoal/acadêmico de portfólio. **Não é** um canal oficial de
> informação do INT/UnB e não tem qualquer afiliação institucional.

Este repositório é um **monorepo** com duas partes:

| Pasta | O que é | Stack |
|-------|---------|-------|
| [`backend/`](backend/) | Scraper + pipeline RAG + API | Python, FastAPI, ChromaDB, Gemini |
| [`frontend/`](frontend/) | Interface de chat | Vite + React |

## Estrutura

```
.
├── backend/      # ver backend/README.md
├── frontend/     # ver frontend/README.md
├── .github/workflows/rescrape.yml   # re-scraping periódico (roda em backend/)
└── CONTEXTO_PROJETO.md              # decisões de projeto
```

## Como rodar (resumo)

```bash
# 1. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha GEMINI_API_KEY
python -m scripts.run_pipeline      # popula o vector store
uvicorn src.api.main:app --reload   # http://localhost:8000/docs

# 2. Frontend (em outro terminal)
cd frontend
npm install
cp .env.example .env        # ajuste VITE_API_URL se necessário
npm run dev                 # http://localhost:5173
```

Detalhes em [`backend/README.md`](backend/README.md) e [`frontend/README.md`](frontend/README.md).
