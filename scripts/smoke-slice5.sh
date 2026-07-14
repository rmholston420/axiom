#!/usr/bin/env bash
set -euo pipefail

echo "== API health =="
curl -sS http://localhost:7200/health | python3 -m json.tool

echo
echo "== Council health =="
curl -sS http://localhost:7201/health | python3 -m json.tool

echo
echo "== Council direct =="
curl -sS -X POST http://localhost:7201/council \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the most important open problems in quantum computing?","council_size":2,"mode":"sequential"}' \
  | python3 -m json.tool

echo
echo "== Council via API proxy =="
curl -sS -X POST http://localhost:7200/council \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the most important open problems in quantum computing?","council_size":2,"mode":"sequential"}' \
  | python3 -m json.tool
