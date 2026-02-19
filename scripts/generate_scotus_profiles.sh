#!/usr/bin/env bash
set -euo pipefail

# Generate SCOTUS justice profiles via Ollama (Bay Tides).
# Required env:
#   OLLAMA_HOST (e.g. https://ollama.baytides.org)
# Optional env:
#   OLLAMA_MODEL (default: llama3.2)
#   DATABASE_URL (or pass --db)
#   PROFILE_LIMIT (default: 20)
#   FORCE_PROFILES (true/false)

PROFILE_LIMIT=${PROFILE_LIMIT:-20}
FORCE_PROFILES=${FORCE_PROFILES:-false}

DB_ARG=()
if [[ -n "${DATABASE_URL:-}" ]]; then
  DB_ARG=(--db "$DATABASE_URL")
fi

FORCE_ARG=()
if [[ "$FORCE_PROFILES" == "true" ]]; then
  FORCE_ARG=(--force)
fi

echo "[1/3] Syncing justice metadata"
python -m civitas.cli scotus sync-justices "${DB_ARG[@]}"

echo "[2/3] Ingesting recent SCOTUS opinions"
python -m civitas.cli ingest scotus "${DB_ARG[@]}"

echo "[3/3] Generating justice profiles"
python -m civitas.cli scotus generate-profiles \
  --limit "$PROFILE_LIMIT" \
  "${FORCE_ARG[@]}" \
  "${DB_ARG[@]}"
