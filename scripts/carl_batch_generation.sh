#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Carl AI Batch Content Generation
# =============================================================================
# Generates all missing content in batches with progress tracking.
# Designed for long-running operation with recovery support.
#
# Usage:
#   ./carl_batch_generation.sh [--analyses-only|--recommendations-only]
#
# Environment:
#   DATABASE_URL       - Database path (default: civitas.db)
#   OLLAMA_HOST        - Ollama server (default: http://localhost:11434)
#   OLLAMA_MODEL       - Model to use (default: llama3.1:8b-instruct-q8_0)
#   BATCH_SIZE         - Items per batch (default: 25)
#   SLEEP_BETWEEN      - Seconds between batches (default: 5)
#   MAX_BATCHES        - Max batches per run, 0=unlimited (default: 0)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CIVITAS_ROOT="${SCRIPT_DIR}/.."
PYTHON_BIN="${PYTHON_BIN:-/opt/civitas/.venv/bin/python}"
LOG_FILE="${LOG_FILE:-/var/log/civitas/carl_batch.log}"

# Defaults
BATCH_SIZE="${BATCH_SIZE:-25}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-5}"
MAX_BATCHES="${MAX_BATCHES:-0}"
REFRESH_DAYS="${REFRESH_DAYS:-30}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b-instruct-q8_0}"

# Parse args
RUN_ANALYSES=true
RUN_RECOMMENDATIONS=true
if [[ "${1:-}" == "--analyses-only" ]]; then
    RUN_RECOMMENDATIONS=false
elif [[ "${1:-}" == "--recommendations-only" ]]; then
    RUN_ANALYSES=false
fi

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg"
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

get_stats() {
    ${PYTHON_BIN} -c "
import sqlite3
import os

db_path = os.environ.get('DATABASE_URL', 'civitas.db')
if db_path.startswith('sqlite:///'):
    db_path = db_path[10:]

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM project2025_policies')
total = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM resistance_analyses WHERE generated_at IS NOT NULL')
analyzed = cur.fetchone()[0]

cur.execute('SELECT COUNT(DISTINCT p2025_policy_id) FROM resistance_recommendations')
with_recs = cur.fetchone()[0]

print(f'{total},{analyzed},{with_recs}')
"
}

log "=============================================="
log "Carl AI Batch Content Generation"
log "=============================================="
log "Model: ${OLLAMA_MODEL}"
log "Batch size: ${BATCH_SIZE}"
log "Sleep between batches: ${SLEEP_BETWEEN}s"
log "Max batches: ${MAX_BATCHES:-unlimited}"
log ""

# Get initial stats
IFS=',' read -r total analyzed with_recs <<< "$(get_stats)"
missing_analyses=$((total - analyzed))
missing_recs=$((total - with_recs))

log "Current status:"
log "  Total policies: ${total}"
log "  With analyses: ${analyzed} (missing: ${missing_analyses})"
log "  With recommendations: ${with_recs} (missing: ${missing_recs})"
log ""

# Export for Python
export OLLAMA_MODEL

# =============================================================================
# Phase 1: Generate Analyses
# =============================================================================
if [[ "$RUN_ANALYSES" == "true" ]] && [[ $missing_analyses -gt 0 ]]; then
    log "Phase 1: Generating ${missing_analyses} missing analyses..."

    batch_count=0
    while true; do
        # Check remaining
        IFS=',' read -r total analyzed _ <<< "$(get_stats)"
        remaining=$((total - analyzed))

        if [[ $remaining -le 0 ]]; then
            log "All analyses complete!"
            break
        fi

        batch_count=$((batch_count + 1))
        if [[ $MAX_BATCHES -gt 0 ]] && [[ $batch_count -gt $MAX_BATCHES ]]; then
            log "Reached max batches (${MAX_BATCHES}), stopping analyses phase"
            break
        fi

        log "Batch ${batch_count}: Processing up to ${BATCH_SIZE} analyses (${remaining} remaining)..."

        ${PYTHON_BIN} -m civitas.cli resist analyze-batch \
            --limit "${BATCH_SIZE}" \
            --refresh-days "${REFRESH_DAYS}" \
            2>&1 | while IFS= read -r line; do log "  $line"; done

        if [[ $SLEEP_BETWEEN -gt 0 ]]; then
            log "Sleeping ${SLEEP_BETWEEN}s before next batch..."
            sleep "${SLEEP_BETWEEN}"
        fi
    done

    log "Phase 1 complete. Processed ${batch_count} batches."
fi

# =============================================================================
# Phase 2: Generate Recommendations
# =============================================================================
if [[ "$RUN_RECOMMENDATIONS" == "true" ]]; then
    IFS=',' read -r total _ with_recs <<< "$(get_stats)"
    missing_recs=$((total - with_recs))

    if [[ $missing_recs -gt 0 ]]; then
        log ""
        log "Phase 2: Generating ${missing_recs} missing recommendations..."

        batch_count=0
        while true; do
            # Check remaining
            IFS=',' read -r total _ with_recs <<< "$(get_stats)"
            remaining=$((total - with_recs))

            if [[ $remaining -le 0 ]]; then
                log "All recommendations complete!"
                break
            fi

            batch_count=$((batch_count + 1))
            if [[ $MAX_BATCHES -gt 0 ]] && [[ $batch_count -gt $MAX_BATCHES ]]; then
                log "Reached max batches (${MAX_BATCHES}), stopping recommendations phase"
                break
            fi

            log "Batch ${batch_count}: Processing up to ${BATCH_SIZE} recommendations (${remaining} remaining)..."

            ${PYTHON_BIN} -m civitas.cli resist recommend-batch \
                --limit "${BATCH_SIZE}" \
                2>&1 | while IFS= read -r line; do log "  $line"; done

            if [[ $SLEEP_BETWEEN -gt 0 ]]; then
                log "Sleeping ${SLEEP_BETWEEN}s before next batch..."
                sleep "${SLEEP_BETWEEN}"
            fi
        done

        log "Phase 2 complete. Processed ${batch_count} batches."
    fi
fi

# =============================================================================
# Summary
# =============================================================================
log ""
log "=============================================="
log "Generation Complete"
log "=============================================="
IFS=',' read -r total analyzed with_recs <<< "$(get_stats)"
log "Final status:"
log "  Total policies: ${total}"
log "  With analyses: ${analyzed} ($(( analyzed * 100 / total ))%)"
log "  With recommendations: ${with_recs} ($(( with_recs * 100 / total ))%)"
log "=============================================="
