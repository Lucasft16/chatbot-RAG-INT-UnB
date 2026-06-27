"""Schemas Pydantic de request/response da API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pergunta do usuário (em português).")


class Source(BaseModel):
    url: str
    title: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = Field(default_factory=list)
