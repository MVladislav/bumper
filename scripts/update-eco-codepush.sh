#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[ERROR] Line $LINENO: $BASH_COMMAND" >&2' ERR
trap 'if [ -n "${TMP_DIR:-}" ]; then rm -rf "$TMP_DIR"; fi' EXIT

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
BASE_URL="https://codepush-base.dc-na.ww.ecouser.net/v0.1/public/codepush/update_check"
OUTPUT_FOLDER="json_mappings"
COMBINED_FILE="$OUTPUT_FOLDER/updateCheck.json"

JSON_SOURCE_INFO="./bumper/web/static_api/codePushConfig.json"
JSON_RESULT="./bumper/web/static_api/updateCheck.json"
PARALLEL="${ECO_PARALLEL:-4}"

mkdir -p "$OUTPUT_FOLDER"

log() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*" >&2; }
err() { echo "[ERROR] $*" >&2; }

# Dependency checks
command -v jq >/dev/null 2>&1 || { err "jq required"; exit 1; }
command -v curl >/dev/null 2>&1 || { err "curl required"; exit 1; }

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

TMP_DIR="$(mktemp -d)"
FRAG_DIR="$TMP_DIR/fragments"
STAT_DIR="$TMP_DIR/status"
mkdir -p "$FRAG_DIR" "$STAT_DIR"

# Fetches run in parallel; each worker writes one fragment file and one status
# file (ok / skipped / failed), both named after the deployment key.
mark() { printf '%s\n' "$2" > "$STAT_DIR/$1"; }
process_key() {
  local dk="$1" raw_result cleaned

  raw_result=$(default_curl GET "$BASE_URL?app_version=1.0.0&deployment_key=$dk" 2>/dev/null || true)

  if [ -z "$raw_result" ]; then
    echo "  ✗ $dk: empty response" >&2
    mark "$dk" failed
    return 0
  fi

  if ! jq -e . >/dev/null 2>&1 <<<"$raw_result"; then
    echo "  ✗ $dk: invalid JSON response" >&2
    mark "$dk" failed
    return 0
  fi

  # Check download_url
  if ! jq -e '.update_info.download_url != ""' >/dev/null 2>&1 <<<"$raw_result"; then
    echo "  - $dk: skipped (empty download_url)" >&2
    mark "$dk" skipped
    return 0
  fi

  # Clean URL (remove AWS query params)
  cleaned=$(jq '
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
  ' <<<"$raw_result")

  jq --arg dk "$dk" '{($dk): .}' <<<"$cleaned" > "$FRAG_DIR/$dk"
  mark "$dk" ok
  echo "  ✓ $dk: success"
}
export -f process_key default_curl mark
export BASE_URL USER_AGENT FRAG_DIR STAT_DIR

echo "----------------------------------------"
printf '%s\n' "${deployment_keys[@]}" | xargs -P "$PARALLEL" -n 1 bash -c 'process_key "$@"' _
echo "----------------------------------------"

success_count=0
skipped_empty_url=0
failed_keys=()
for dk in "${deployment_keys[@]}"; do
  case "$(cat "$STAT_DIR/$dk" 2>/dev/null || echo failed)" in
    ok) ((++success_count)) ;;
    skipped) ((++skipped_empty_url)) ;;
    failed) failed_keys+=("$dk") ;;
  esac
done

log "Processed: ${#deployment_keys[@]}"
log "Success:   $success_count"
log "Skipped:   $skipped_empty_url"
log "Failed:    ${#failed_keys[@]}"

if [ "$success_count" -eq 0 ]; then
  err "No valid results to combine"
  exit 1
fi

# Combine fragments; keys sorted explicitly so the output is deterministic
# across runs and machines (glob order would depend on the locale).
jq -s 'add | to_entries | sort_by(.key) | from_entries' "$FRAG_DIR"/* > "$COMBINED_FILE"

log "Saved combined JSON → $COMBINED_FILE"

cp "$COMBINED_FILE" "$JSON_RESULT"
log "Updated result file → $JSON_RESULT"

if [ ${#failed_keys[@]} -gt 0 ]; then
  warn "Failed keys:"
  printf '  %s\n' "${failed_keys[@]}"
fi
