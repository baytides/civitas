#!/bin/bash
# Download Open States bulk data (PostgreSQL dump)
# Run on Carl to get comprehensive state legislature data

set -e

DATA_DIR="/opt/civitas/data/openstates"
DUMP_URL="https://data.openstates.org/postgres/monthly/2026-01-public.pgdump"
DUMP_FILE="$DATA_DIR/openstates-latest.pgdump"

echo "=== Open States Bulk Data Download ==="
echo "Source: https://open.pluralpolicy.com/data/"
echo ""

# Create data directory
mkdir -p "$DATA_DIR"

# Download the PostgreSQL dump (about 9GB)
echo "Downloading PostgreSQL dump (~9GB)..."
echo "URL: $DUMP_URL"
echo "This will take a while depending on connection speed."
echo ""

cd "$DATA_DIR"

# Use wget with resume capability
if command -v wget &> /dev/null; then
    wget -c -O "$DUMP_FILE" "$DUMP_URL"
else
    curl -C - -o "$DUMP_FILE" "$DUMP_URL"
fi

echo ""
echo "Download complete!"
echo "File: $DUMP_FILE"
echo "Size: $(du -h "$DUMP_FILE" | cut -f1)"

echo ""
echo "=== Next Steps ==="
echo "The dump is in PostgreSQL custom format."
echo "To use this data, you can:"
echo "1. Restore to a PostgreSQL database:"
echo "   pg_restore -d openstates openstates-latest.pgdump"
echo ""
echo "2. Convert to CSV/JSON for direct import to Civitas SQLite"
echo "   (requires PostgreSQL installed locally)"
echo ""
echo "For Civitas integration, we'll extract the relevant tables:"
echo "- opencivicdata_bill (legislation)"
echo "- opencivicdata_person (legislators)"
echo "- opencivicdata_votecount (votes)"
echo ""
