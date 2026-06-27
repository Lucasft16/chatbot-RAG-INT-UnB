FROM python:3.12-slim

WORKDIR /app

# Dependências primeiro (melhor cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
# O chroma_db/ persistido é comitado no repo e copiado junto.
COPY chroma_db/ ./chroma_db/

# Roda como usuário não-root (boa prática de segurança); o chown garante que o
# appuser possa ler/escrever no chroma_db (o SQLite precisa de lock de escrita).
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
