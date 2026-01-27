#!/usr/bin/env bash
set -euo pipefail

# Generates expert-mode resistance content via Carl (Ollama).
# Required env:
#   DATABASE_URL (or pass --db)
#   OLLAMA_HOST (Carl VM, e.g. http://20.98.70.48:11434)
# Optional env:
#   OLLAMA_MODEL (default: llama3.2)
#   ANALYZE_LIMIT (default: 100)
#   ANALYZE_REFRESH_DAYS (default: 30)
#   RECOMMEND_LIMIT (default: 100)
#   RECOMMEND_TIER (optional)
#   FORCE_RECOMMEND (true/false)

ANALYZE_LIMIT=${ANALYZE_LIMIT:-100}
ANALYZE_REFRESH_DAYS=${ANALYZE_REFRESH_DAYS:-30}
RECOMMEND_LIMIT=${RECOMMEND_LIMIT:-100}
RECOMMEND_TIER=${RECOMMEND_TIER:-}
FORCE_RECOMMEND=${FORCE_RECOMMEND:-false}

DB_ARG=()
if [[ -n "${DATABASE_URL:-}" ]]; then
  DB_ARG=(--db "$DATABASE_URL")
fi

TIER_ARG=()
if [[ -n "$RECOMMEND_TIER" ]]; then
  TIER_ARG=(--tier "$RECOMMEND_TIER")
fi

FORCE_ARG=()
if [[ "$FORCE_RECOMMEND" == "true" ]]; then
  FORCE_ARG=(--force)
fi

echo "[1/2] Generating expert analyses (limit=${ANALYZE_LIMIT}, refresh_days=${ANALYZE_REFRESH_DAYS})"
python -m civitas.cli resist analyze-batch \
  --limit "$ANALYZE_LIMIT" \
  --refresh-days "$ANALYZE_REFRESH_DAYS" \
  "${DB_ARG[@]}"

echo "[2/2] Generating resistance recommendations (limit=${RECOMMEND_LIMIT})"
python -m civitas.cli resist recommend-batch \
  --limit "$RECOMMEND_LIMIT" \
  "${TIER_ARG[@]}" \
  "${FORCE_ARG[@]}" \
  "${DB_ARG[@]}"
