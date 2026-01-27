#!/bin/bash
# Download Open States bulk data (PostgreSQL dump)
# Run on Carl to get comprehensive state legislature data
#
# This bypasses the 500 requests/day API limit by downloading
# the complete PostgreSQL monthly dump (~9GB)
#
# Source: https://open.pluralpolicy.com/data/
# License: Public Domain

set -e

DATA_DIR="/opt/civitas/data/openstates"
YEAR_MONTH=$(date +%Y-%m)
DUMP_URL="https://data.openstates.org/postgres/monthly/${YEAR_MONTH}-public.pgdump"
DUMP_FILE="$DATA_DIR/openstates-${YEAR_MONTH}.pgdump"
LATEST_LINK="$DATA_DIR/openstates-latest.pgdump"

echo "=== Open States Bulk Data Download ==="
echo "Source: https://open.pluralpolicy.com/data/"
echo "Month: ${YEAR_MONTH}"
echo ""

# Create data directory
mkdir -p "$DATA_DIR"

# Check if file already exists
if [ -f "$DUMP_FILE" ]; then
    echo "Dump file for ${YEAR_MONTH} already exists."
    echo "File: $DUMP_FILE"
    echo "Size: $(du -h "$DUMP_FILE" | cut -f1)"
    echo ""
    if [ "$1" != "--force" ]; then
        echo "Use --force to re-download."
        exit 0
    fi
    echo "Force flag set, re-downloading..."
fi

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

# Create/update latest symlink
ln -sf "$(basename "$DUMP_FILE")" "$LATEST_LINK"

echo ""
echo "Download complete!"
echo "File: $DUMP_FILE"
echo "Size: $(du -h "$DUMP_FILE" | cut -f1)"
echo "Symlink: $LATEST_LINK"

echo ""
echo "=== Next Steps ==="
echo "The dump is in PostgreSQL custom format."
echo ""
echo "To extract and import to Civitas:"
echo "  civitas ingest-openstates-bulk $DUMP_FILE"
echo ""
echo "Or manually restore to PostgreSQL first:"
echo "  createdb openstates_temp"
echo "  pg_restore -d openstates_temp $DUMP_FILE"
echo ""
echo "Key tables in the dump:"
echo "- opencivicdata_bill (legislation)"
echo "- opencivicdata_person (legislators)"
echo "- opencivicdata_organization (chambers, committees)"
echo "- opencivicdata_votecount (roll call votes)"
echo "- opencivicdata_jurisdiction (states)"
echo ""
