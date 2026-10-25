#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR
# ==============================================================================
# Ecovacs API Sync Script
# Requirements: curl, jq, openssl
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../shared/paths.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../shared/eco-auth.sh"
trap 'eco_cleanup' EXIT

# Dependency checks
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl required" >&2; exit 1; }

# --- Configuration ------------------------------------------------------------
COUNTRIES=("DE" "US" "JP")
# Read by the sourced eco-auth.sh library.
# shellcheck disable=SC2034
LOGIN_COUNTRY="${COUNTRIES[0]}"

TARGET_JSON_PATH="$REPO_ROOT/bumper/web/static_api"

# --- Login --------------------------------------------------------------------
eco_login || exit 1

# --- Step 4: Download & combine config files ----------------------------------
echo "📥 Step 4: Downloading config files..."
# API_URL="https://portal${CONTINENT_POSTFIX}.ecouser.net/api"
OUTPUT_FOLDER="$(abspath json_mappings)"
mkdir -p "$OUTPUT_FOLDER"
declare -A FILES=(
  ["pim/product/getConfigGroups"]="configGroupsResponse"
  ["pim/product/getConfignetAll"]="configNetAllResponse"
  ["pim/product/getProductIotMap"]="productIotMap"
)

for ENDPOINT in $(printf '%s\n' "${!FILES[@]}" | sort); do
  OUTBASE="${FILES[$ENDPOINT]}"
  echo "  📡 Fetching '$ENDPOINT':"
  for COUNTRY_CODE in "${COUNTRIES[@]}"; do
    API_URL="https://portal$(get_continent_postfix "$COUNTRY_CODE").ecouser.net/api"
    BODY=$(
      jq -n \
        --arg defaultLang "en" \
        --arg version "v2" \
        --arg lang "EN" \
        --arg country "$COUNTRY_CODE" \
        --arg userid "$USER_ID" \
        --arg token "$USER_TOKEN" \
        --arg resource "$DEVICE_ID" \
        --arg realm "$REALM" \
        '{
          defaultLang: $defaultLang,
          version: $version,
          lang: $lang,
          country: $country,
          auth: {
            with: "users",
            userid: $userid,
            realm: $realm,
            token: $token,
            resource: $resource
          }
        }'
    )
    OUTFILE="$OUTPUT_FOLDER/${OUTBASE}V2-${COUNTRY_CODE}.json"
    echo "    ⬇️ Fetching '$ENDPOINT' for '$COUNTRY_CODE' -> '$OUTFILE'"
    default_curl POST "$API_URL/$ENDPOINT" -H "Content-Type: application/json" -d "$BODY" | jq . >"$OUTFILE"
    if jq -e '.code == 0 or .code == "0000"' "$OUTFILE" >/dev/null; then
      jq '.data' "$OUTFILE" >"$OUTFILE.tmp" && mv "$OUTFILE.tmp" "$OUTFILE"
      echo "    🔄 Parsed 'data' for '$COUNTRY_CODE'"
    else
      echo "    ⚠️ Warning: '$OUTFILE' did not return code 0, removing it so it is not combined." >&2
      rm -f "$OUTFILE"
    fi
  done
done

# --- Step 5: Combine config files ---------------------------------------------
echo "🛠️ Step 5: Combining config files (country priority: DE > US > other)..."
# Recursively sort object keys so upstream key reordering does not change the
# combined output (stable diffs, same output every run).
# shellcheck disable=SC2016  # $key/$in are jq variables, not bash expansions
JQ_NORMALIZE='def walk(f): . as $in | if type == "object" then reduce keys_unsorted[] as $key ({}; . + {($key): ($in[$key] | walk(f))}) | f elif type == "array" then map(walk(f)) | f else f end; '
JQ_SORT_KEYS='walk(if type == "object" then (to_entries | sort_by(.key) | from_entries) else . end)'

# Per-file combine rules: unique key, ordering, optional per-entry extra.
declare -A COMBINE_SPECS=(
  ["configGroupsResponse"]='unique_by(.id) | sort_by(.sort, .id) | map(if .robots != null then .robots |= sort_by(.sort, .groupId) else . end)'
  ["configNetAllResponse"]='unique_by(.groupId) | sort_by(.sort, .groupId)'
  ["productIotMap"]='unique_by(.classid) | sort_by(.classid)'
)

# Country priority: DE first, then US, then the remaining countries in order.
PRIORITY_COUNTRIES=()
for c in DE US; do
  if [[ " ${COUNTRIES[*]} " == *" $c "* ]]; then PRIORITY_COUNTRIES+=("$c"); fi
done
for c in "${COUNTRIES[@]}"; do
  if [[ " ${PRIORITY_COUNTRIES[*]} " != *" $c "* ]]; then PRIORITY_COUNTRIES+=("$c"); fi
done

for ENDPOINT in $(printf '%s\n' "${!FILES[@]}" | sort); do
  OUTBASE="${FILES[$ENDPOINT]}"
  echo "  🔀 Combining JSON '$OUTBASE'"

  COMBINED_FILE="$OUTPUT_FOLDER/${OUTBASE}Combined.json"
  # Only combine valid country responses, in country priority order.
  FILES_TO_COMBINE=()
  for COUNTRY_CODE in "${PRIORITY_COUNTRIES[@]}"; do
    FILE="$OUTPUT_FOLDER/${OUTBASE}V2-${COUNTRY_CODE}.json"
    if [[ -s "$FILE" ]] && jq -e 'type == "array"' "$FILE" >/dev/null 2>&1; then
      FILES_TO_COMBINE+=("$FILE")
    else
      echo "    ⚠️ Skipping invalid or missing '$FILE'"
    fi
  done

  if [ ${#FILES_TO_COMBINE[@]} -gt 0 ]; then
    # First occurrence wins per unique key, so an entry present in a
    # higher-priority country is preferred; the committed target file is
    # appended last, keeping entries no country supplies anymore.
    jq -s "${JQ_NORMALIZE}add | ${COMBINE_SPECS[$OUTBASE]} | ${JQ_SORT_KEYS}" \
      "${FILES_TO_COMBINE[@]}" "${TARGET_JSON_PATH}/${OUTBASE}.json" >"$COMBINED_FILE"
    cp "$COMBINED_FILE" "${TARGET_JSON_PATH}/${OUTBASE}.json"
    echo "    ✅ Combined JSON '$OUTBASE' :: copied JSON: '$COMBINED_FILE' -> '${TARGET_JSON_PATH}/${OUTBASE}.json'"
  fi
done

# --- Step 6: Replacing URLs in combined JSON files-----------------------------
echo "🧼 Step 6: Replacing URLs in combined JSON files..."
REPLACEMENTS=(
  "api-app.dc-na.ww"
  "api-app.dc-eu.ww"
  "api-app.dc-as.ww"
)

for OUTBASE in "configNetAllResponse" "productIotMap" "configGroupsResponse"; do
  JSON_FILE="${TARGET_JSON_PATH}/${OUTBASE}.json"
  echo "  🌐 Processing $JSON_FILE"

  for OLD_DOMAIN in "${REPLACEMENTS[@]}"; do
    sed -i "s|https://$OLD_DOMAIN|https://portal-ww|g" "$JSON_FILE"
  done

  echo "    🔁 URLs replaced in $JSON_FILE"
done

echo "🎉 Done! Files saved in '$OUTPUT_FOLDER'"
