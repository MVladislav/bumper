#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[ERROR] Line $LINENO: $BASH_COMMAND" >&2' ERR
trap 'warn "Interrupted - saving..."' INT TERM
trap 'result' EXIT

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
JSON_SOURCE_INFO="./bumper/web/static_api/updateCheck.json"
OUTPUT_FOLDER="./json_mappings"
OUTPUT_FILE="$OUTPUT_FOLDER/updateCheck_mapping.json"

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

success_count=0
failed_count=0
declare -A folder_mapping=()

main() {
  if [ ${#mappings[@]} -eq 0 ]; then
    err "No valid download_urls found in $JSON_SOURCE_INFO"
    exit 1
  fi

  log "Found ${#mappings[@]} deployments to process"

  echo "----------------------------------------"
  download
  echo "----------------------------------------"
  log "Processed: ${#mappings[@]}"
  log "Success:   $success_count"
  log "Failed:    $failed_count"
}

download() {
  for mapping in "${mappings[@]}"; do
    IFS=' ' read -r deployment_key download_url <<< "$mapping"
    echo "Processing: $deployment_key"
    zip_file="$OUTPUT_FOLDER/${deployment_key}.zip"

    # Download zip
    echo "  Downloading..."
    result=$(default_curl GET "$download_url" "$zip_file")
    http_code="${result%%::*}"
    file_size="${result##*::}"

    if [ "$http_code" != "200" ] || [ "$file_size" = "0" ]; then
      echo "    ✗ Download failed (HTTP $http_code, size $file_size)" >&2
      ((++failed_count))
      rm -f "$zip_file"
      continue
    fi

    # Verify file exists and has content
    if [ ! -s "$zip_file" ]; then
      echo "    ✗ Empty file downloaded" >&2
      ((++failed_count))
      rm -f "$zip_file"
      continue
    fi

    # Get main folder with unzip -Z -1
    main_folder="$(unzip -Z -1 "$zip_file" 2>/dev/null | cut -d/ -f1 | head -1)"

    if [ -n "$main_folder" ] && [ "$main_folder" != "" ]; then
      echo "    ✓ $deployment_key = $main_folder"
      folder_mapping["$deployment_key"]="$main_folder"
      ((++success_count))
    else
      echo "    ✗ Could not determine main folder" >&2
      ((++failed_count))
    fi

    # Cleanup
    rm -f "$zip_file"
  done
}

result() {
  if [ ${#folder_mapping[@]} -eq 0 ]; then
    warn "No folder mappings found - empty file created"
    echo '' > "$OUTPUT_FILE"
    return 0
  fi

  {
    echo '{'
    for deployment_key in "${!folder_mapping[@]}"; do
      main_folder="${folder_mapping[$deployment_key]}"
      printf "  '%s': '%s',\n" "$main_folder" "$deployment_key"
    done
    echo '}'
  } > "$OUTPUT_FILE"

  log "Saved Python mapping → $OUTPUT_FILE (${#folder_mapping[@]} entries)"
}

main
