FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/packages:/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi==0.111.1 \
    uvicorn[standard]==0.30.3 \
    httpx \
    pydantic==2.8.2 \
    pydantic-settings \
    neo4j \
    redis \
    python-dotenv

COPY apps/api ./apps/api
COPY packages ./packages

EXPOSE 7200
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD curl -f http://localhost:7200/health || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "7200"]
