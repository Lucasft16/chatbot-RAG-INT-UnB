"""Configuração central do backend, carregada do `.env`."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provedor de LLM / Embeddings (Gemini)
    gemini_api_key: str = ""
    gemini_generation_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Cache do crawl (páginas coletadas)
    raw_data_dir: str = "data/raw"

    # Vector store
    chroma_db_dir: str = "chroma_db"
    chroma_collection: str = "int_unb"

    # Retrieval
    retrieval_top_k: int = 5

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
