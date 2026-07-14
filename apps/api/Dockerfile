# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first for layer caching
COPY pyproject.toml ./

# Install the monorepo Python dependencies
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi>=0.111.1 \
    "uvicorn[standard]>=0.29.0" \
    neo4j>=5.0.0 \
    httpx>=0.27.0 \
    redis>=5.0.0 \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0"

# Copy application source
COPY apps/api/ ./apps/api/
COPY packages/ ./packages/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 7200

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7200/health || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "7200"]
