#!/usr/bin/env bash
set -euo pipefail

MANUALS_DIR="$(cd "$(dirname "$0")/../pdf_manuals" && pwd)"
ALB="${ALB:-}"

if [[ -z "$ALB" ]]; then
  echo "Error: ALB env var not set. Run: export ALB=http://your-alb-url"
  exit 1
fi

INGEST_URL="$ALB/ingest"
UPLOADED_FILE="already_uploaded.json"

find "$MANUALS_DIR" -mindepth 2 -maxdepth 2 -name "*.pdf" | sort | while read -r PDF; do
  VEHICLE_DIR="$(dirname "$PDF")"
  VEHICLE_NAME="$(basename "$VEHICLE_DIR" | tr '_' ' ')"
  FILENAME="$(basename "$PDF")"
  DOCUMENT_NAME="${FILENAME%.pdf}"
  TRACKER="$VEHICLE_DIR/$UPLOADED_FILE"

  # Check if already uploaded
  if [[ -f "$TRACKER" ]] && python3 -c "
import json, sys
data = json.load(open('$TRACKER'))
sys.exit(0 if '$FILENAME' in data else 1)
" 2>/dev/null; then
    echo "Skipping $VEHICLE_NAME / $DOCUMENT_NAME (already uploaded)"
    continue
  fi

  echo "Uploading $VEHICLE_NAME / $DOCUMENT_NAME..."

  RESPONSE=$(curl -sf -X POST "$INGEST_URL" \
    -F "vehicle_name=$VEHICLE_NAME" \
    -F "document_name=$DOCUMENT_NAME" \
    -F "file=@$PDF")

  JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
  echo "  Job ID: $JOB_ID"

  # Poll until done
  while true; do
    STATUS_RESP=$(curl -sf "$ALB/ingest/$JOB_ID")
    STATUS=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

    if [[ "$STATUS" == "done" ]]; then
      echo "  Done."
      break
    elif [[ "$STATUS" == "error" ]]; then
      DETAIL=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('detail', 'unknown'))")
      echo "  Error: $DETAIL"
      break
    else
      ETA=$(echo "$STATUS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('completed_chunks','?')}/{d.get('total_chunks','?')} chunks, ETA {d.get('eta_seconds','?')}s\")" 2>/dev/null || echo "$STATUS")
      echo "  $ETA"
      sleep 5
    fi
  done

  # Mark as uploaded only on success
  if [[ "$STATUS" == "done" ]]; then
    python3 -c "
import json, os
tracker = '$TRACKER'
data = json.load(open(tracker)) if os.path.exists(tracker) else []
if '$FILENAME' not in data:
    data.append('$FILENAME')
json.dump(data, open(tracker, 'w'), indent=2)
"
  fi

done

echo "All done."
