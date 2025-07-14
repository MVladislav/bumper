#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 file1.json [file2.json ...]"
  exit 1
fi

OUTPUT_FILE="configGroupsResponseCombined.json"

jq -s '
  # 1) Merge all files into one big array
  add
  # 2) Sort by top‑level .id so duplicates become adjacent
  | sort_by(.id)
  # 3) Bucket by .id
  | group_by(.id)
  # 4) For each bucket, keep the first object (regardless of content)
  | map(.[0])
  # 5) Final sort by .id
  | sort_by(.id)
' "$@" >"$OUTPUT_FILE"

echo "✅ Combined JSON written to: $OUTPUT_FILE"
