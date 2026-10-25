#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR
# ==============================================================================
# Ecovacs Voice Sync Script
#
# Fetches the voice files the robot downloads to change its voice language, and
# the metadata that tells the app which file belongs to which language.
#
# The files are a few MB each and are NOT part of the repository: they land in
# the voice directory (BUMPER_VOICES) and the user has to run this script before
# the server starts if the robot should be able to switch its language.
#
# Run it before the DNS override is in place, or from a machine that can still
# reach the Ecovacs cloud - the DNS change points the cloud names at Bumper.
#
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
# The paths are absolute, so the script writes to the same place no matter which
# directory it is run from.
VOICE_DIR="$(abspath "${BUMPER_VOICES:-${BUMPER_DATA:-$REPO_ROOT/data}/voices}")"
METADATA_FILE="$REPO_ROOT/bumper/web/static_api/voices.json"
# The languages to fetch, comma separated. Empty means every language the app
# offers. Every language needs a file for the robot to be able to switch to it.
VOICE_LANGS="${VOICE_LANGS:-}"
MID="p95mgv"
VOICE_ID="default"
CONTINENT_POSTFIX="$(get_continent_postfix "$LOGIN_COUNTRY")"

# --- Login --------------------------------------------------------------------
eco_login || exit 1

# --- Helpers ------------------------------------------------------------------
# Call a portal API with the account auth and return the body.
call_portal_api() {
  local endpoint="$1" body="$2"
  local url
  url="https://portal${CONTINENT_POSTFIX}.ecouser.net/api/$endpoint"
  default_curl POST "$url" -H "Content-Type: application/json" -d "$body"
}

# Build the auth block every portal call carries.
auth_block() {
  jq -n \
    --arg userid "$USER_ID" \
    --arg token "$USER_TOKEN" \
    --arg resource "$DEVICE_ID" \
    --arg realm "$REALM" \
    '{
      with: "users",
      userid: $userid,
      realm: $realm,
      token: $token,
      resource: $resource
    }'
}

# --- Step 1: The languages the app offers --------------------------------------
echo "📋 Step 1: Fetching the offered languages..."
LANGUAGES_RESP="$(call_portal_api "pim/v2/voice/getLanuages" "$(jq -n --arg mid "$MID" --argjson auth "$(auth_block)" '{mid: $mid, auth: $auth, channel: "google_play"}')")"
if [[ "$(jq -r '.code // empty' <<<"$LANGUAGES_RESP")" != "0" ]]; then
  echo "❌ getLanuages failed: $LANGUAGES_RESP" >&2
  exit 1
fi
OFFERED_LANGS="$(jq -r '.voices[]?.voiceLang' <<<"$LANGUAGES_RESP")"
echo "  🌐 Offered: $(tr '\n' ' ' <<<"$OFFERED_LANGS")"

# --- Step 2: The voice of every language ---------------------------------------
echo "📥 Step 2: Fetching the voice of every language..."
mkdir -p "$VOICE_DIR"
VOICES_JSON="{}"
FAILED_LANGS=()

for LANG_CODE in $OFFERED_LANGS; do
  if [[ -n "$VOICE_LANGS" ]] && ! grep -qw "$LANG_CODE" <<<"${VOICE_LANGS//,/ }"; then
    echo "  ⚠️ Skipping '$LANG_CODE': not requested"
    continue
  fi

  echo "  📡 Fetching the voice of '$LANG_CODE':"
  VOICE_RESP="$(call_portal_api "pim/voice/get" "$(jq -n \
    --arg voiceLang "${LANG_CODE^^}" \
    --arg mid "$MID" \
    --arg id "$VOICE_ID" \
    --argjson auth "$(auth_block)" \
    '{voiceLang: $voiceLang, mid: $mid, id: $id, auth: $auth, channel: "google_play"}')")"

  if [[ "$(jq -r '.code // empty' <<<"$VOICE_RESP")" != "0" ]]; then
    echo "    ❌ voice/get failed: $VOICE_RESP" >&2
    FAILED_LANGS+=("$LANG_CODE")
    continue
  fi

  VOICE_PACK_ID="$(jq -r '.voices[0].id // empty' <<<"$VOICE_RESP")"
  VOICE_URL="$(jq -r '.voices[0].voiceUrl // empty' <<<"$VOICE_RESP")"
  VOICE_MD5="$(jq -r '.voices[0].voiceMd5 // empty' <<<"$VOICE_RESP")"
  VOICE_SIZE="$(jq -r '.voices[0].voiceSize // 0' <<<"$VOICE_RESP")"
  DOWNLOAD_ID="${VOICE_URL##*/}"

  if [[ -z "$VOICE_URL" || -z "$DOWNLOAD_ID" ]]; then
    echo "    ❌ No voice file for '$LANG_CODE'" >&2
    FAILED_LANGS+=("$LANG_CODE")
    continue
  fi

  echo "    ⬇️ Downloading '$VOICE_URL' -> '$VOICE_DIR/$DOWNLOAD_ID'"
  if ! curl -k -sSfL --connect-timeout 10 --max-time 300 -o "$VOICE_DIR/$DOWNLOAD_ID" "$VOICE_URL"; then
    echo "    ❌ Download failed for '$LANG_CODE'" >&2
    FAILED_LANGS+=("$LANG_CODE")
    continue
  fi

  # The robot checks the checksum, so a file that does not match is useless.
  LOCAL_MD5="$(md5_file "$VOICE_DIR/$DOWNLOAD_ID")"
  if [[ -n "$VOICE_MD5" && "$LOCAL_MD5" != "$VOICE_MD5" ]]; then
    echo "    ❌ Checksum mismatch for '$LANG_CODE': expected '$VOICE_MD5', got '$LOCAL_MD5'" >&2
    rm -f "$VOICE_DIR/$DOWNLOAD_ID"
    FAILED_LANGS+=("$LANG_CODE")
    continue
  fi

  # The metadata points at Bumper, not at the cloud.
  VOICES_JSON="$(jq --arg lang "$LANG_CODE" --arg id "$VOICE_PACK_ID" --arg md5 "$VOICE_MD5" --arg size "$VOICE_SIZE" \
    --arg voice "$(jq -r '.voices[0].voice // empty' <<<"$VOICE_RESP")" \
    --arg icon "$(jq -r '.voices[0].iconUrl // empty' <<<"$VOICE_RESP")" \
    --arg sample "$(jq -r '.voices[0].sampleVoiceUrl // empty' <<<"$VOICE_RESP")" \
    --arg name "$(jq -r '.voices[0].name // empty' <<<"$VOICE_RESP")" \
    --arg sort "$(jq -r '.voices[0].sort // 0' <<<"$VOICE_RESP")" \
    --arg times "$(jq -r '.voices[0].downloadTimes // 0' <<<"$VOICE_RESP")" \
    --arg download "$DOWNLOAD_ID" \
    '. + {($lang): {
        id: $id,
        name: $name,
        voice: $voice,
        iconUrl: $icon,
        sampleVoiceUrl: $sample,
        voiceUrl: ("/api/pim/voice/download/" + $download),
        voiceMd5: $md5,
        voiceSize: ($size | tonumber),
        sort: ($sort | tonumber),
        downloadTimes: ($times | tonumber)
      }}' <<<"$VOICES_JSON")"

  echo "    ✅ '$LANG_CODE' stored"
done

# --- Step 3: Write the metadata ------------------------------------------------
if [[ "$(jq 'length' <<<"$VOICES_JSON")" == "0" ]]; then
  echo "❌ No voice fetched, the metadata file was not written." >&2
  exit 1
fi

echo "🧼 Step 3: Writing the metadata..."
# The URLs of the icons and samples point at the cloud; they are served by
# Bumper as well, so keep the path.
VOICES_JSON="$(jq 'with_entries(
  .value |= (
    (.iconUrl |= (if type == "string" then sub("^https?://[^/]+"; "") else . end)) |
    (.sampleVoiceUrl |= (if type == "string" then sub("^https?://[^/]+"; "") else . end))
  )
)' <<<"$VOICES_JSON")"
mkdir -p "$(dirname "$METADATA_FILE")"
jq . <<<"$VOICES_JSON" >"$METADATA_FILE"
echo "  ✅ Metadata written to '$METADATA_FILE'"

if [[ ${#FAILED_LANGS[@]} -gt 0 ]]; then
  echo "⚠️ Failed languages: ${FAILED_LANGS[*]}" >&2
  exit 1
fi

echo "🎉 Done! Voice files in '$VOICE_DIR', metadata in '$METADATA_FILE'"
echo "   Start Bumper with BUMPER_VOICES='$VOICE_DIR' to use them."
