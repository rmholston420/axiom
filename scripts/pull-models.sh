#!/usr/bin/env bash
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

pull_model() {
  local model="$1"
  echo "Pulling ${model}..."
  curl -fsS "${OLLAMA_URL}/api/pull" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${model}\",\"stream\":false}"
  echo
}

pull_model "llama3.2:3b"
pull_model "qwen3-coder:latest"

echo "Available models:"
curl -fsS "${OLLAMA_URL}/api/tags"
echo
