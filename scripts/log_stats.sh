#!/bin/bash
# Log current generation stats from the Civitas API
set -e

LOG_FILE="${LOG_FILE:-/var/log/civitas/stats.log}"
API_URL="${API_URL:-http://localhost:8000/api/v1/status}"

# Fetch stats and format output
stats=$(curl -s "$API_URL")

if [ -z "$stats" ] || [ "$stats" = "null" ]; then
    echo "[$(date -Iseconds)] ERROR: Could not fetch stats from $API_URL" >> "$LOG_FILE"
    exit 1
fi

# Parse JSON and format log entry
timestamp=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('generated_at', 'unknown'))" 2>/dev/null || echo "$(date -Iseconds)")
objectives_total=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('objectives_total', 0))" 2>/dev/null || echo "0")
expert_analyses=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expert_analyses', 0))" 2>/dev/null || echo "0")
expert_pct=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expert_analyses_pct', 0))" 2>/dev/null || echo "0")
insights=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('objectives_with_insights', 0))" 2>/dev/null || echo "0")
insights_pct=$(echo "$stats" | python3 -c "import sys,json; print(json.load(sys.stdin).get('objectives_insight_pct', 0))" 2>/dev/null || echo "0")

echo "[$timestamp] Objectives: $objectives_total, Analyses: $expert_analyses/$objectives_total (${expert_pct}%), Insights: $insights/$objectives_total (${insights_pct}%)" >> "$LOG_FILE"

# Also output to stdout for systemd journal
echo "Stats logged: Analyses $expert_analyses/$objectives_total (${expert_pct}%), Insights $insights/$objectives_total (${insights_pct}%)"
