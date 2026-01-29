#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Local Batch Content Generation (Mac with Ollama)
# =============================================================================
# Generates all missing content using local Ollama (M3 Pro is much faster)
# Run this script in background: nohup ./scripts/local_batch_generation.sh &
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CIVITAS_ROOT="${SCRIPT_DIR}/.."
cd "$CIVITAS_ROOT"

# Activate virtual environment
source .venv/bin/activate

# Configuration
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b-instruct-q8_0}"
DB_PATH="${DB_PATH:-civitas_carl.db}"
LOG_FILE="${LOG_FILE:-/tmp/civitas_local_batch.log}"
BATCH_SIZE="${BATCH_SIZE:-25}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-2}"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

get_stats() {
    python -c "
from sqlalchemy import create_engine, text

engine = create_engine('sqlite:///${DB_PATH}')
with engine.connect() as conn:
    total = conn.execute(text('SELECT COUNT(*) FROM project2025_policies')).scalar()
    analyzed = conn.execute(text('SELECT COUNT(*) FROM resistance_analyses WHERE generated_at IS NOT NULL')).scalar()
    with_recs = conn.execute(text('SELECT COUNT(DISTINCT p2025_policy_id) FROM resistance_recommendations')).scalar()
    print(f'{total},{analyzed},{with_recs}')
"
}

log "=============================================="
log "Local Batch Content Generation (Mac)"
log "=============================================="
log "Ollama host: ${OLLAMA_HOST}"
log "Model: ${OLLAMA_MODEL}"
log "Database: ${DB_PATH}"
log "Batch size: ${BATCH_SIZE}"
log ""

# Get initial stats
IFS=',' read -r total analyzed with_recs <<< "$(get_stats)"
missing_analyses=$((total - analyzed))
missing_recs=$((total - with_recs))

log "Initial status:"
log "  Total policies: ${total}"
log "  With analyses: ${analyzed} (missing: ${missing_analyses})"
log "  With recommendations: ${with_recs} (missing: ${missing_recs})"
log ""

# =============================================================================
# Phase 1: Generate Analyses
# =============================================================================
if [[ $missing_analyses -gt 0 ]]; then
    log "Phase 1: Generating ${missing_analyses} missing analyses..."

    batch_count=0
    while true; do
        IFS=',' read -r total analyzed _ <<< "$(get_stats)"
        remaining=$((total - analyzed))

        if [[ $remaining -le 0 ]]; then
            log "All analyses complete!"
            break
        fi

        batch_count=$((batch_count + 1))
        log "Batch ${batch_count}: Processing up to ${BATCH_SIZE} analyses (${remaining} remaining)..."

        python -m civitas.cli resist analyze-batch \
            --limit "${BATCH_SIZE}" \
            --refresh-days 30 \
            --db "sqlite:///${DB_PATH}" \
            2>&1 | while IFS= read -r line; do log "  $line"; done

        if [[ $SLEEP_BETWEEN -gt 0 ]]; then
            sleep "${SLEEP_BETWEEN}"
        fi
    done

    log "Phase 1 complete. Processed ${batch_count} batches."
fi

# =============================================================================
# Phase 2: Generate Recommendations
# =============================================================================
IFS=',' read -r total _ with_recs <<< "$(get_stats)"
missing_recs=$((total - with_recs))

if [[ $missing_recs -gt 0 ]]; then
    log ""
    log "Phase 2: Generating ${missing_recs} missing recommendations..."

    batch_count=0
    while true; do
        IFS=',' read -r total _ with_recs <<< "$(get_stats)"
        remaining=$((total - with_recs))

        if [[ $remaining -le 0 ]]; then
            log "All recommendations complete!"
            break
        fi

        batch_count=$((batch_count + 1))
        log "Batch ${batch_count}: Processing up to ${BATCH_SIZE} recommendations (${remaining} remaining)..."

        python -m civitas.cli resist recommend-batch \
            --limit "${BATCH_SIZE}" \
            --db "sqlite:///${DB_PATH}" \
            2>&1 | while IFS= read -r line; do log "  $line"; done

        if [[ $SLEEP_BETWEEN -gt 0 ]]; then
            sleep "${SLEEP_BETWEEN}"
        fi
    done

    log "Phase 2 complete. Processed ${batch_count} batches."
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
log ""
log "To sync back to Carl:"
log "  scp ${DB_PATH} carl:/opt/civitas/civitas.db"
