#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[ERROR] Line $LINENO: $BASH_COMMAND" >&2' ERR
trap 'warn "Interrupted - saving..."' INT TERM
trap 'result; if [ -n "${TMP_DIR:-}" ]; then rm -rf "$TMP_DIR"; fi' EXIT

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
JSON_SOURCE_INFO="./bumper/web/static_api/updateCheck.json"
OUTPUT_FOLDER="./json_mappings"
OUTPUT_FILE="$OUTPUT_FOLDER/updateCheck_mapping.json"
JSON_RESULT="./bumper/web/static_api/updateCheck_mapping.json"
PARALLEL="${ECO_PARALLEL:-4}"

mkdir -p "$OUTPUT_FOLDER"

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }
err() { echo "[ERROR] $*" >&2; }

# Dependency checks
command -v jq >/dev/null 2>&1 || { err "jq required"; exit 1; }
command -v curl >/dev/null 2>&1 || { err "curl required"; exit 1; }
command -v unzip >/dev/null 2>&1 || { err "unzip required"; exit 1; }

default_curl() {
  local method="$1" url="$2" output="$3"
  shift 3
  curl -sSfkL --connect-timeout 10 --max-time 30 \
    -X "$method" \
    -H "User-Agent: $USER_AGENT" \
    -w "%{http_code}::%{size_download}" \
    --url "$url" \
    -o "$output" \
    "$@"
}

log "Processing $JSON_SOURCE_INFO"

# Extract all deployment_key -> download_url mappings
mapfile -t mappings < <(
  jq -r '.[] | select(.update_info.download_url != null and .update_info.download_url != "") |
         "\(.update_info.deployment_key) \(.update_info.download_url)"' "$JSON_SOURCE_INFO"
)

if [ ${#mappings[@]} -eq 0 ]; then
  err "No valid download_urls found in $JSON_SOURCE_INFO"
  exit 1
fi

log "Found ${#mappings[@]} deployments to process"

TMP_DIR="$(mktemp -d)"
RESULT_DIR="$TMP_DIR/results"
mkdir -p "$RESULT_DIR"

# Downloads and folder extraction run in parallel; each worker writes
# "main_folder<TAB>deployment_key" into its own result file.
process_one() {
  local deployment_key="$1" download_url="$2"
  local zip_file main_folder dl_result http_code file_size

  dl_result=$(default_curl GET "$download_url" "$OUTPUT_FOLDER/${deployment_key}.zip")
  http_code="${dl_result%%::*}"
  file_size="${dl_result##*::}"

  zip_file="$OUTPUT_FOLDER/${deployment_key}.zip"
  if [ "$http_code" != "200" ] || [ "$file_size" = "0" ]; then
    echo "  ✗ $deployment_key: download failed (HTTP $http_code, size $file_size)" >&2
    rm -f "$zip_file"
    return 0
  fi

  # Get main folder (first path component of the first entry that has one)
  main_folder="$(unzip -Z -1 "$zip_file" 2>/dev/null | awk -F/ 'NF > 1 { print $1 }' | head -1 || true)"

  if [ -n "$main_folder" ]; then
    echo "  ✓ $deployment_key = $main_folder"
    printf '%s\t%s\n' "$main_folder" "$deployment_key" > "$RESULT_DIR/$deployment_key"
  else
    echo "  ✗ $deployment_key: could not determine main folder" >&2
  fi

  rm -f "$zip_file"
}
export -f process_one default_curl
export OUTPUT_FOLDER RESULT_DIR USER_AGENT

echo "----------------------------------------"
printf '%s\n' "${mappings[@]}" | xargs -P "$PARALLEL" -n 2 bash -c 'process_one "$@"' _
echo "----------------------------------------"

result_count=0
if [ -n "${RESULT_DIR:-}" ] && [ -n "$(find "$RESULT_DIR" -mindepth 1 -maxdepth 1 -type f 2>/dev/null)" ]; then
  result_count="$(find "$RESULT_DIR" -mindepth 1 -maxdepth 1 -type f | wc -l)"
fi
log "Processed: ${#mappings[@]}"
log "Success:   $result_count"
log "Failed:    $(( ${#mappings[@]} - result_count ))"

result() {
  if [ -n "${RESULT_DIR:-}" ] && [ -n "$(find "$RESULT_DIR" -mindepth 1 -maxdepth 1 -type f 2>/dev/null)" ]; then
    # Valid JSON: {"main_folder": "deployment_key", ...}
    # Sorted by main folder (with deployment key as tie-break) so the output
    # is deterministic across runs — parallel downloads finish in a different
    # order every time.
    jq -Rn '
      [inputs | select(length > 0) | split("\t")] |
      map({key: .[0], value: .[1]}) | sort_by(.key, .value) | from_entries
    ' "$RESULT_DIR"/* > "$OUTPUT_FILE"
    cp "$OUTPUT_FILE" "$JSON_RESULT"
    log "Saved mapping → $OUTPUT_FILE ($(jq length "$OUTPUT_FILE" 2>/dev/null || echo 0) entries)"
    log "Copied result file → $JSON_RESULT"
  else
    warn "No folder mappings found - leaving $JSON_RESULT unchanged"
  fi
}
