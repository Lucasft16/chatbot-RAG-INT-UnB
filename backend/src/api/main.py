"""Ponto de entrada da API FastAPI.

Rodar localmente:
    uvicorn src.api.main:app --reload
Docs interativas: http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import chat
from src.config import settings

app = FastAPI(
    title="INT/UnB Chatbot RAG",
    description="API RAG que responde sobre o site do INT/UnB. "
    "Projeto pessoal/acadêmico — não é canal oficial do INT/UnB.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
