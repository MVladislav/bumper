#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 file1.json [file2.json ...]"
  exit 1
fi

OUTPUT_FILE="configNetAllResponseCombined.json"

# Merge all JSON arrays, flatten, remove duplicates by groupId, and sort
jq -s 'add | unique_by(.groupId) | sort_by(.groupId)' "$@" >"$OUTPUT_FILE"

echo "✅ Combined JSON written to: $OUTPUT_FILE"
