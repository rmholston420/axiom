# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
    fastapi>=0.111.1 \
    "uvicorn[standard]>=0.29.0" \
    neo4j>=5.0.0 \
    httpx>=0.27.0 \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0"

COPY apps/axiomatizer/ ./apps/axiomatizer/
COPY packages/ ./packages/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 7202

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7202/health || exit 1

CMD ["uvicorn", "apps.axiomatizer.main:app", "--host", "0.0.0.0", "--port", "7202"]
