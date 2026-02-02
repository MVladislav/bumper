#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
BASE_URL="https://codepush-base.dc-na.ww.ecouser.net/v0.1/public/codepush/update_check"
OUTPUT_FOLDER="json_mappings"
COMBINED_FILE="$OUTPUT_FOLDER/updateCheck.json"
mkdir -p "$OUTPUT_FOLDER"

JSON_FILE="./bumper/web/static_web/codePushConfig.json"

default_curl() {
  local m="$1" u="$2"
  shift 2
  curl -k -s -X "$m" -H "User-Agent: $USER_AGENT" --url "$u" "$@"
}

mapfile -t deployment_keys < <(jq -r '.[] | .. | .deploymentKey? | .production? | select(. != null)' "$JSON_FILE")

if [ ${#deployment_keys[@]} -eq 0 ]; then
  echo "No production deployment keys found in $JSON_FILE"
  exit 1
fi

echo "Found ${#deployment_keys[@]} production deployment keys"
success_count=0
failed_keys=()
skipped_empty_url=0

declare -A json_results=()
for i in "${!deployment_keys[@]}"; do
  dk="${deployment_keys[$i]}"
  echo "  Processing $dk (${i}/${#deployment_keys[@]})"

  raw_result=$(default_curl GET "$BASE_URL?app_version=1.0.0&deployment_key=$dk" 2>/dev/null || true)

  if [ -n "$raw_result" ] && echo "$raw_result" | jq -e . >/dev/null 2>&1; then
    if echo "$raw_result" | jq -e '.update_info.download_url != ""' >/dev/null 2>&1; then
      json_fragment=$(echo "$raw_result" | jq --arg dk "$dk" '{($dk): .}')
      json_results["$dk"]="$json_fragment"
      ((++success_count))
      echo "    ✓ Success (has download URL)"
    else
      ((++skipped_empty_url))
      echo "    - Skipped (empty download_url)"
    fi
  else
    echo "    ✗ Failed or empty response"
    failed_keys+=("$dk")
  fi
done

echo "Successfully processed: $success_count/${#deployment_keys[@]}"
echo "Skipped empty download_url: $skipped_empty_url"

if [ ${#json_results[@]} -eq 0 ]; then
  echo "No valid responses with download_url to combine"
  exit 1
fi

echo "${json_results[@]}" | jq -s 'add' > "$COMBINED_FILE"

if [ ${#failed_keys[@]} -gt 0 ]; then
  echo "Failed keys (${#failed_keys[@]}): ${failed_keys[*]}"
fi

echo "Combined results saved to $COMBINED_FILE"
