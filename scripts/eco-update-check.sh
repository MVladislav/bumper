#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[ERROR] Line $LINENO: $BASH_COMMAND" >&2' ERR

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
BASE_URL="https://codepush-base.dc-na.ww.ecouser.net/v0.1/public/codepush/update_check"
OUTPUT_FOLDER="json_mappings"
COMBINED_FILE="$OUTPUT_FOLDER/updateCheck.json"

JSON_SOURCE_INFO="./bumper/web/static_api/codePushConfig.json"
JSON_RESULT="./bumper/web/static_api/updateCheck.json"

mkdir -p "$OUTPUT_FOLDER"

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }
err() { echo "[ERROR] $*" >&2; }

default_curl() {
  local method="$1" url="$2"
  shift 2
  curl -sSfkL --connect-timeout 10 --max-time 20 \
    -X "$method" \
    -H "User-Agent: $USER_AGENT" \
    --url "$url" "$@"
}

log "Reading deployment keys from $JSON_SOURCE_INFO"

mapfile -t deployment_keys < <(
  jq -r '.[] | .. | .deploymentKey? | .production? | select(. != null)' "$JSON_SOURCE_INFO"
)

if [ ${#deployment_keys[@]} -eq 0 ]; then
  err "No production deployment keys found in $JSON_SOURCE_INFO"
  exit 1
fi

log "Found ${#deployment_keys[@]} deployment keys"
success_count=0
failed_keys=()
skipped_empty_url=0

echo "----------------------------------------"
declare -A json_results=()
for i in "${!deployment_keys[@]}"; do
  dk="${deployment_keys[$i]}"
  echo "Processing [$((i+1))/${#deployment_keys[@]}]: $dk"

  raw_result=$(default_curl GET "$BASE_URL?app_version=1.0.0&deployment_key=$dk" 2>/dev/null || true)

  if [ -z "$raw_result" ]; then
    echo "    ✗ Empty response" >&2
    failed_keys+=("$dk")
    continue
  fi

  if ! echo "$raw_result" | jq -e . >/dev/null 2>&1; then
    echo "    ✗ Invalid JSON response" >&2
    failed_keys+=("$dk")
    continue
  fi

  # Check download_url
  if ! echo "$raw_result" | jq -e '.update_info.download_url != ""' >/dev/null 2>&1; then
    echo "    - Skipped (empty download_url)" >&2
    ((++skipped_empty_url))
    continue
  fi

  # Clean URL (remove AWS query params)
  cleaned=$(echo "$raw_result" | jq '
    .update_info.download_url |= (
      if type != "string" then .
      else
        split("?") as $p
        | if ($p | length) == 1 then .
          else
            (
              $p[1]
              | split("&")
              | map(select(
                  (. | startswith("AWSAccessKeyId=") or
                    startswith("Expires=") or
                    startswith("Signature=")) | not
                ))
            ) as $filtered
            | if ($filtered | length) == 0 then
                $p[0]   # no params left → no "?"
              else
                $p[0] + "?" + ($filtered | join("&"))
              end
          end
      end
    )
  ')

  json_fragment=$(echo "$cleaned" | jq --arg dk "$dk" '{($dk): .}')
  json_results["$dk"]="$json_fragment"
  ((++success_count))
  echo "    ✓ Success"
done

echo "----------------------------------------"
log "Processed: ${#deployment_keys[@]}"
log "Success:   $success_count"
log "Skipped:   $skipped_empty_url"
log "Failed:    ${#failed_keys[@]}"

if [ ${#json_results[@]} -eq 0 ]; then
  err "No valid results to combine"
  exit 1
fi

printf '%s\n' "${json_results[@]}" | jq -s 'add' > "$COMBINED_FILE"

log "Saved combined JSON → $COMBINED_FILE"

cp "$COMBINED_FILE" "$JSON_RESULT"
log "Updated result file → $JSON_RESULT"

if [ ${#failed_keys[@]} -gt 0 ]; then
  warn "Failed keys:"
  printf '  %s\n' "${failed_keys[@]}"
fi
