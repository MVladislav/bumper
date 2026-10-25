#!/usr/bin/env bash
set -euo pipefail
# ==============================================================================
# Ecovacs Firmware Helper Script
# Requirements: curl, jq, base64
# ==============================================================================

# Ensure required env vars
if [[ -z "${ECO_MODEL:-}" || -z "${ECO_CURRENT_FW_VER:-}" ]]; then
  echo "❌ ERROR: Please set ECO_MODEL and ECO_CURRENT_FW_VER environment variables." >&2
  exit 1
fi

# --- Configuration ------------------------------------------------------------
BASE_URL=https://portal-ww.ecouser.net:443/api/ota/products/wukong/class
MODEL="$ECO_MODEL"
CURRENT_FW_VER="$ECO_CURRENT_FW_VER"
# PLATFORM=Android
MODULE=fw0 # fw0 | AIConfig

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
FIRMWARE_DL_ENABLE=${ECO_FIRMWARE_DL_ENABLE:-0}
FIRMWARE_DL_DIR="./x-bot-firmware-downloads"

# Create download directory if it doesn't exist
mkdir -p "$FIRMWARE_DL_DIR"

# --- Helpers ------------------------------------------------------------------
default_curl() {
  local m="$1" u="$2"
  shift 2
  curl -k -s -X "$m" -H "User-Agent: $USER_AGENT" --url "$u" "$@"
}

# --- Step 1: Check Firmware ---------------------------------------------------
echo "🔍 Checking for firmware updates..."
FIRMWARE_CHECK_URL="${BASE_URL}/${MODEL}/firmware/latest.json?ver=${CURRENT_FW_VER}&module=${MODULE}"
FIRMWARE_CHECK_RESP=$(default_curl GET "$FIRMWARE_CHECK_URL" --get)

# --- Step 2: Parse and Report -------------------------------------------------
if [[ "$FIRMWARE_CHECK_RESP" == "Not Found" ]]; then
  echo "  ✅ No new firmware available or your provided version is unknown. You are on the latest known version: ${CURRENT_FW_VER}"
else
  echo "  📦 New firmware available!"
  VERSION_NAME=$(jq -r '.name // "unknown"' <<< "$FIRMWARE_CHECK_RESP")
  VERSION=$(jq -r --arg m "$MODULE" '.[$m].version // "unknown"' <<< "$FIRMWARE_CHECK_RESP")
  SIZE=$(jq -r --arg m "$MODULE" '.[$m].size // "unknown"' <<< "$FIRMWARE_CHECK_RESP")
  CHECKSUM=$(jq -r --arg m "$MODULE" '.[$m].checkSum // "unknown"' <<< "$FIRMWARE_CHECK_RESP")
  URL=$(jq -r --arg m "$MODULE" '.[$m].url // "unknown"' <<< "$FIRMWARE_CHECK_RESP")
  CHANGELOG_B64=$(jq -r --arg m "$MODULE" '.[$m].changeLog // ""' <<< "$FIRMWARE_CHECK_RESP")
  CHANGELOG=$(echo "$CHANGELOG_B64" | base64 --decode 2>/dev/null || echo "(Failed to decode changelog)")

  echo "    🆕 Version:   $VERSION :: $VERSION_NAME"
  echo "    📦 Size:      $SIZE bytes"
  echo "    🔒 Checksum:  $CHECKSUM"
  echo "    🔗 URL:       $URL"
  echo "    📝 Changelog:"
  echo "         => $CHANGELOG"

  if [[ $FIRMWARE_DL_ENABLE -eq 1 ]]; then
    # --- Step 3: Download Firmware ----------------------------------------------
    FILENAME="firmware-${MODEL}-${VERSION}-${CHECKSUM}.bin"
    DEST="${FIRMWARE_DL_DIR}/${FILENAME}"

    echo
    echo "⬇️  Downloading firmware to: $DEST"
    curl -sL -o "$DEST"_TMP "$URL" && mv "$DEST"_TMP "$DEST"

    echo "  ✅ Firmware downloaded successfully!"
    echo "  📁 Saved to: $DEST"
  fi
fi

echo
echo "🎉 Done!"
