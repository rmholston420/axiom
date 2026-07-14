#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== docker ps =="
docker compose ps

echo
echo "== axiom health =="
make health

echo
echo "== integration tests =="
pytest -m integration
