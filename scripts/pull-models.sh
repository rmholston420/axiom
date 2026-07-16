#!/usr/bin/env bash
set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

pull_model() {
  local model="$1"
  echo "Pulling ${model}..."
  curl -fsS "${OLLAMA_URL}/api/pull"     -H "Content-Type: application/json"     -d "{"model":"${model}","stream":false}"
  echo
}

MODELS=(
  "llama3.2:3b"
  "llama3.1:8b"
  "deepseek-r1:7b"
  "deepseek-r1:14b"
  "phi4-mini:3.8b"
  "phi4:14b"
  "qwen3:14b"
  "qwen2.5-coder:7b"
  "qwen2.5-coder:14b"
  "qwen3-coder:latest"
  "mistral:7b"
  "stable-code:3b"
  "starcoder2:3b"
  "codellama:13b"
  "nomic-embed-text"
)

for model in "${MODELS[@]}"; do
  pull_model "$model"
done

echo "Available models:"
curl -fsS "${OLLAMA_URL}/api/tags"
echo
