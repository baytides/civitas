#!/bin/bash
# =============================================================================
# Civitas Full Data Ingestion Script
# =============================================================================
# This script ingests data from all available sources:
# - Direct state scrapers (California, etc.)
# - CourtListener (federal court opinions)
# - Congress.gov (federal legislation)
# - Federal Register (executive orders)
# - Supreme Court (slip opinions)
# - Project 2025 PDF
#
# Required Environment Variables:
#   COURTLISTENER_TOKEN - Get from https://www.courtlistener.com/sign-in/
#   CONGRESS_API_KEY - Get from https://api.congress.gov/sign-up/
#
# Usage:
#   nohup /opt/civitas/scripts/full_ingestion.sh > /opt/civitas/logs/full_ingest.log 2>&1 &
# =============================================================================

set -e

# Configuration
CIVITAS_DIR="/opt/civitas"
LOG_DIR="$CIVITAS_DIR/logs"
DB_URL="sqlite:////opt/civitas/civitas.db"

# Create log directory
mkdir -p "$LOG_DIR"

# Activate virtual environment
cd "$CIVITAS_DIR"
source .venv/bin/activate
export DATABASE_URL="$DB_URL"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=========================================="
log "Starting Full Civitas Data Ingestion"
log "=========================================="

# -----------------------------------------------------------------------------
# 1. FEDERAL LEGISLATION (Congress.gov)
# -----------------------------------------------------------------------------
log ""
log "=== FEDERAL LEGISLATION ==="

# Current Congress (119th)
log "Ingesting 119th Congress laws..."
civitas ingest federal 119 --laws-only || log "WARNING: 119th Congress ingestion failed"

# Previous Congress (118th)
log "Ingesting 118th Congress laws..."
civitas ingest federal 118 --laws-only || log "WARNING: 118th Congress ingestion failed"

# -----------------------------------------------------------------------------
# 2. EXECUTIVE ORDERS (Federal Register)
# -----------------------------------------------------------------------------
log ""
log "=== EXECUTIVE ORDERS ==="

for year in 2025 2024 2023; do
    log "Ingesting $year executive orders..."
    civitas ingest executive-orders --year $year --db "$DB_URL" || log "WARNING: $year EO ingestion failed"
done

# -----------------------------------------------------------------------------
# 3. SUPREME COURT OPINIONS
# -----------------------------------------------------------------------------
log ""
log "=== SUPREME COURT ==="

for term in 2024 2023 2022; do
    log "Ingesting SCOTUS term $term..."
    civitas ingest scotus --term $term || log "WARNING: SCOTUS $term ingestion failed"
done

# -----------------------------------------------------------------------------
# 4. STATE LEGISLATURES (Direct Scrapers)
# -----------------------------------------------------------------------------
log ""
log "=== STATE LEGISLATURES (Direct Scrapers) ==="

# Use direct scrapers for available states
log "Checking available state scrapers..."
civitas ingest list-scrapers || log "WARNING: Could not list scrapers"

# Scrape available states
for state in CA; do
    log "Scraping $state legislature..."
    civitas ingest scrape-state --state $state --limit 1000 || log "WARNING: $state scraping failed"
done

# -----------------------------------------------------------------------------
# 5. FEDERAL COURTS (CourtListener)
# -----------------------------------------------------------------------------
log ""
log "=== FEDERAL COURTS (CourtListener) ==="

if [ -z "$COURTLISTENER_TOKEN" ]; then
    log "WARNING: COURTLISTENER_TOKEN not set, skipping CourtListener ingestion"
    log "Get a token at: https://www.courtlistener.com/sign-in/"
else
    export COURTLISTENER_API_TOKEN="$COURTLISTENER_TOKEN"

    # Last 180 days of federal court opinions
    log "Ingesting federal court opinions (last 180 days)..."
    civitas ingest courts --days 180 || log "WARNING: CourtListener ingestion failed"
fi

# -----------------------------------------------------------------------------
# 6. CALIFORNIA LEGISLATURE (Direct Download)
# -----------------------------------------------------------------------------
log ""
log "=== CALIFORNIA LEGISLATURE ==="

# California has its own data download that doesn't need OpenStates
for year in 2025 2023 2021 2019; do
    log "Ingesting California $year session..."
    civitas ingest california $year || log "WARNING: California $year ingestion failed"
done

# -----------------------------------------------------------------------------
# 7. PROJECT 2025
# -----------------------------------------------------------------------------
log ""
log "=== PROJECT 2025 ==="

PDF_PATH="$CIVITAS_DIR/data/project2025/mandate_for_leadership.pdf"
if [ -f "$PDF_PATH" ]; then
    log "Ingesting Project 2025 document..."
    civitas ingest project2025 --pdf "$PDF_PATH" || log "WARNING: Project 2025 ingestion failed"
else
    log "WARNING: Project 2025 PDF not found at $PDF_PATH"
    log "Download from: https://s3.documentcloud.org/documents/24088042/project-2025s-mandate-for-leadership-the-conservative-promise.pdf"
fi

# -----------------------------------------------------------------------------
# 8. US CONSTITUTION
# -----------------------------------------------------------------------------
log ""
log "=== US CONSTITUTION ==="
log "Ingesting US Constitution..."
civitas ingest us-constitution || log "WARNING: US Constitution ingestion failed"

# -----------------------------------------------------------------------------
# 9. STATE CONSTITUTIONS
# -----------------------------------------------------------------------------
log ""
log "=== STATE CONSTITUTIONS ==="
log "Ingesting state constitutions..."
civitas ingest constitutions || log "WARNING: State constitutions ingestion failed"

# -----------------------------------------------------------------------------
# FINAL STATISTICS
# -----------------------------------------------------------------------------
log ""
log "=========================================="
log "INGESTION COMPLETE"
log "=========================================="
log ""
log "Database Statistics:"
civitas stats || true

log ""
log "Full ingestion completed at $(date)"
