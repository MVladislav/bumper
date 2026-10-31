#!/usr/bin/env bash
# ==============================================================================
# Ecovacs Firmware Helper Script
#
# Reverse-engineered from ./reverse-engineer/ (decompiled app + captured flows):
#   * Endpoint:  {host}/api/ota/products/wukong/class/{model}/firmware/latest.json
#   * Observed query params (app): did, sn, ver, module, ts, lang, version=v2
#     (a bare `ver=...&module=...` is usually accepted by the portal hosts)
#   * Success answer: HTTP 200 JSON with `version`, `name`, `force` and a per
#     module object (`version`, `size`, `checkSum`, `changeLog`, `url`, ...).
#   * "No update / unknown version / bad params" answer: HTTP 404 with the
#     plain-text body "Not Found".
#   * Hosts are per-region shards: portal*.ecouser.net (legacy) and
#     api-app*.ecouser.net (modern). Set ECO_BASE_URL to target a specific one.
#
# Requirements: curl, jq, base64
# ==============================================================================
set -euo pipefail

# --- Argument parsing ---------------------------------------------------------
ENUMERATE=0
DEEP=0
for arg in "$@"; do
  case "$arg" in
    --enumerate|-e) ENUMERATE=1 ;;
    --deep|-d) DEEP=1 ;;
    --help|-h)
      cat <<'EOF'
Usage: ECO_MODEL=... ECO_CURRENT_FW_VER=... ./check-eco-firmware.sh [options]

Options:
  -e, --enumerate   Enable the extended version enumeration / debug check.
  -d, --deep        With --enumerate, also probe patch-level versions (X.Y.Z).

Environment variables:
  ECO_MODEL                 Device model (e.g. p95mgv)                     (required)
  ECO_CURRENT_FW_VER        Firmware version the robot runs (e.g. 1.7.2)   (required*)
  ECO_ENUM_TARGET_VERSION   Version to enumerate up to (defaults to ECO_CURRENT_FW_VER)
  ECO_BASE_URL              API base URL (default: https://portal-ww.ecouser.net:443/api/ota/products/wukong/class)
  ECO_MODULE                Module name (default: fw0; or AIConfig)
  ECO_DID / ECO_SN          Device id / serial (optional, improves fidelity)
  ECO_LANG                  Language code (default: en)
  ECO_API_VERSION           API version param (default: unset; set to v2 to match app)
  ECO_ENUM_DEEP=1           Enable deep (patch-level) enumeration
  ECO_ENUM_MAX_PATCH        Highest patch number to probe in deep mode (default: 9)
  ECO_ENUM_DELAY            Delay between probes in seconds (default: 0.1)
  ECO_TIMEOUT               HTTP timeout in seconds (default: 15)
  ECO_FIRMWARE_DL_ENABLE    Download firmware when an update is found (0/1)

* In enumeration mode ECO_CURRENT_FW_VER may be omitted if ECO_ENUM_TARGET_VERSION is set.
EOF
      exit 0
      ;;
    *)
      echo "❌ Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

# Honour env-based toggles too.
ENUMERATE=${ECO_ENUMERATE:-$ENUMERATE}
DEEP=${ECO_ENUM_DEEP:-$DEEP}

# --- Configuration ------------------------------------------------------------
BASE_URL="${ECO_BASE_URL:-https://portal-ww.ecouser.net:443/api/ota/products/wukong/class}"
MODEL="${ECO_MODEL:-}"
CURRENT_FW_VER="${ECO_CURRENT_FW_VER:-}"
MODULE="${ECO_MODULE:-fw0}"
USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
FIRMWARE_DL_ENABLE="${ECO_FIRMWARE_DL_ENABLE:-0}"
FIRMWARE_DL_DIR="./x-bot-firmware-downloads"
TIMEOUT="${ECO_TIMEOUT:-15}"
LANG_CODE="${ECO_LANG:-en}"
DID="${ECO_DID:-}"
SN="${ECO_SN:-}"
API_VERSION="${ECO_API_VERSION:-}"
ENUM_DELAY="${ECO_ENUM_DELAY:-0.1}"
ENUM_MAX_PATCH="${ECO_ENUM_MAX_PATCH:-9}"

mkdir -p "$FIRMWARE_DL_DIR"

# --- Helpers ------------------------------------------------------------------
default_curl() {
  local m="$1" u="$2"
  shift 2
  curl -k -s --max-time "$TIMEOUT" -X "$m" -H "User-Agent: $USER_AGENT" --url "$u" "$@"
}

build_url() {
  local ver="$1"
  local url="${BASE_URL}/${MODEL}/firmware/latest.json?ver=${ver}&module=${MODULE}"
  [[ -n "$DID" ]] && url+="&did=${DID}"
  [[ -n "$SN" ]] && url+="&sn=${SN}"
  [[ -n "$LANG_CODE" ]] && url+="&lang=${LANG_CODE}"
  [[ -n "$API_VERSION" ]] && url+="&version=${API_VERSION}"
  printf '%s' "$url"
}

# Globals populated by do_request.
LAST_HTTP=""
LAST_BODY=""
LAST_URL=""
do_request() {
  local ver="$1"
  local url tmp
  url="$(build_url "$ver")"
  tmp="$(mktemp)"
  LAST_HTTP="$(curl -k -s -o "$tmp" -w "%{http_code}" --max-time "$TIMEOUT" \
    -H "User-Agent: $USER_AGENT" "$url" 2>/dev/null)" || LAST_HTTP="000"
  LAST_BODY="$(tr '\n' ' ' <"$tmp" 2>/dev/null || true)"
  rm -f "$tmp"
  LAST_URL="$url"
}

# Returns: not_found | json:<offered> | other
classify_response() {
  local trimmed
  trimmed="$(printf '%s' "$LAST_BODY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$LAST_HTTP" == "404" ]] || [[ "$trimmed" == "Not Found" ]]; then
    printf 'not_found'
    return
  fi
  if [[ "$LAST_BODY" == \{* ]] && jq -e . >/dev/null 2>&1 <<<"$LAST_BODY"; then
    local offered
    offered="$(jq -r '(.version // .fw0.version // .AIConfig.version // "unknown")' <<<"$LAST_BODY" 2>/dev/null || echo unknown)"
    printf 'json:%s' "$offered"
    return
  fi
  printf 'other'
}

# --- Input validation ---------------------------------------------------------
if [[ -z "$MODEL" ]]; then
  echo "❌ ERROR: Please set ECO_MODEL." >&2
  exit 1
fi

TARGET_VERSION="${ECO_ENUM_TARGET_VERSION:-$CURRENT_FW_VER}"

if [[ "$ENUMERATE" == "1" ]]; then
  if [[ -z "$TARGET_VERSION" ]]; then
    echo "❌ ERROR: Enumeration needs ECO_CURRENT_FW_VER or ECO_ENUM_TARGET_VERSION." >&2
    exit 1
  fi
  if [[ ! "$TARGET_VERSION" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    echo "❌ ERROR: Version must look like MAJOR.MINOR.PATCH (got: $TARGET_VERSION)." >&2
    exit 1
  fi
  ENUM_MAJOR="${BASH_REMATCH[1]}"
  ENUM_MAX_MINOR="${BASH_REMATCH[2]}"
  ENUM_MAX_PATCH="${BASH_REMATCH[3]}"
else
  if [[ -z "$CURRENT_FW_VER" ]]; then
    echo "❌ ERROR: Please set ECO_MODEL and ECO_CURRENT_FW_VER." >&2
    exit 1
  fi
fi

# ==============================================================================
# Normal single check
# ==============================================================================
if [[ "$ENUMERATE" != "1" ]]; then
  echo "🔍 Checking for firmware updates..."
  FIRMWARE_CHECK_URL="$(build_url "$CURRENT_FW_VER")"
  echo "   URL: $FIRMWARE_CHECK_URL"
  FIRMWARE_CHECK_RESP="$(curl -k -s --max-time "$TIMEOUT" -H "User-Agent: $USER_AGENT" --url "$FIRMWARE_CHECK_URL" 2>/dev/null || true)"

  FIRMWARE_CHECK_TRIMMED="$(printf '%s' "$FIRMWARE_CHECK_RESP" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$FIRMWARE_CHECK_TRIMMED" == "Not Found" ]]; then
    echo "  ✅ No new firmware available, or the provided version is unknown / params rejected."
    echo "     You are on (or reported as): ${CURRENT_FW_VER}"
  else
    if jq -e . >/dev/null 2>&1 <<<"$FIRMWARE_CHECK_RESP"; then
      echo "  📦 New firmware available!"
      VERSION_NAME="$(jq -r '.name // "unknown"' <<<"$FIRMWARE_CHECK_RESP")"
      VERSION="$(jq -r --arg m "$MODULE" '.[$m].version // "unknown"' <<<"$FIRMWARE_CHECK_RESP")"
      SIZE="$(jq -r --arg m "$MODULE" '.[$m].size // "unknown"' <<<"$FIRMWARE_CHECK_RESP")"
      CHECKSUM="$(jq -r --arg m "$MODULE" '.[$m].checkSum // "unknown"' <<<"$FIRMWARE_CHECK_RESP")"
      URL="$(jq -r --arg m "$MODULE" '.[$m].url // "unknown"' <<<"$FIRMWARE_CHECK_RESP")"
      CHANGELOG_B64="$(jq -r --arg m "$MODULE" '.[$m].changeLog // ""' <<<"$FIRMWARE_CHECK_RESP")"
      CHANGELOG="$(echo "$CHANGELOG_B64" | base64 --decode 2>/dev/null || echo "(Failed to decode changelog)")"

      echo "    🆕 Version:   $VERSION :: $VERSION_NAME"
      echo "    📦 Size:      $SIZE bytes"
      echo "    🔒 Checksum:  $CHECKSUM"
      echo "    🔗 URL:       $URL"
      echo "    📝 Changelog:"
      echo "         => $CHANGELOG"

      if [[ "$FIRMWARE_DL_ENABLE" -eq 1 ]]; then
        FILENAME="firmware-${MODEL}-${VERSION}-${CHECKSUM}.bin"
        DEST="${FIRMWARE_DL_DIR}/${FILENAME}"
        echo
        echo "⬇️  Downloading firmware to: $DEST"
        curl -sL --max-time "$TIMEOUT" -o "${DEST}_TMP" "$URL" && mv "${DEST}_TMP" "$DEST"
        echo "  ✅ Firmware downloaded successfully!"
        echo "  📁 Saved to: $DEST"
      fi
    else
      echo "  ⚠️  Unexpected response (not JSON, not 'Not Found'):"
      echo "     ${FIRMWARE_CHECK_RESP:0:300}"
    fi
  fi

  echo
  echo "🎉 Done!"
  exit 0
fi

# ==============================================================================
# Extended enumeration / debug check
# ==============================================================================
PARALLEL="${ECO_PARALLEL:-4}"

# Build the version list (minor-level, plus patch-level when --deep).
VERSIONS=()
for ((m = 0; m <= ENUM_MAX_MINOR; m++)); do
  VERSIONS+=("${ENUM_MAJOR}.${m}.0")
  if [[ "$DEEP" == "1" ]]; then
    for ((p = 1; p <= ENUM_MAX_PATCH; p++)); do
      VERSIONS+=("${ENUM_MAJOR}.${m}.${p}")
    done
  fi
done

echo "🧪 Extended firmware version enumeration"
echo "   Model:          $MODEL"
echo "   Target version: $TARGET_VERSION  (major=$ENUM_MAJOR, maxMinor=$ENUM_MAX_MINOR)"
echo "   Base URL:       $BASE_URL"
echo "   Params:         module=$MODULE did=${DID:-<unset>} sn=${SN:-<unset>} lang=$LANG_CODE apiVersion=${API_VERSION:-<unset>}"
echo "   Versions:       ${#VERSIONS[@]}  (parallel=$PARALLEL, deep=$DEEP)"
echo
echo "   Note: 'Not Found' is ambiguous (no update available / unknown version /"
echo "         rejected params). This probe reports which version strings yield a"
echo "         real JSON answer, which helps decide whether the params are right."
echo

TMP_DIR="$(mktemp -d)"
STAT_DIR="$TMP_DIR/status"
mkdir -p "$STAT_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

# Worker: probe one version string and store its result.
probe_one() {
  local ver="$1"
  local url tmp http body trimmed cls offered safe
  url="${BASE_URL}/${MODEL}/firmware/latest.json?ver=${ver}&module=${MODULE}"
  [[ -n "${DID:-}" ]] && url+="&did=${DID}"
  [[ -n "${SN:-}" ]] && url+="&sn=${SN}"
  [[ -n "${LANG_CODE:-}" ]] && url+="&lang=${LANG_CODE}"
  [[ -n "${API_VERSION:-}" ]] && url+="&version=${API_VERSION}"
  tmp="$(mktemp)"
  http="$(curl -k -s -o "$tmp" -w "%{http_code}" --max-time "${TIMEOUT:-15}" \
    -H "User-Agent: ${USER_AGENT}" "$url" 2>/dev/null)" || http="000"
  body="$(tr '\n' ' ' <"$tmp" 2>/dev/null || true)"
  rm -f "$tmp"
  trimmed="$(printf '%s' "$body" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$http" == "404" ]] || [[ "$trimmed" == "Not Found" ]]; then
    cls="not_found"; offered="-"
  elif [[ "$body" == \{* ]] && printf '%s' "$body" | jq -e . >/dev/null 2>&1; then
    offered="$(printf '%s' "$body" | jq -r '(.version // .fw0.version // .AIConfig.version // "unknown")' 2>/dev/null || echo unknown)"
    cls="json:${offered}"
  else
    cls="other"; offered="-"
  fi
  safe="${ver//./_}"
  printf '%s\t%s\t%s\t%s\n' "$ver" "$cls" "$http" "$body" >"$STAT_DIR/${safe}.status"
}
export -f probe_one
export BASE_URL MODEL MODULE DID SN LANG_CODE API_VERSION TIMEOUT USER_AGENT STAT_DIR

echo "⏳ Probing..."
printf '%s\n' "${VERSIONS[@]}" | xargs -P "$PARALLEL" -n 1 bash -c 'probe_one "$@"' _

RESULTS_FILE="./firmware-enum-${MODEL}.tsv"
: >"$RESULTS_FILE"
echo -e "requested_ver\toffered_ver\thttp\tbody" >>"$RESULTS_FILE"

HITS=0
MISSES=0
OTHERS=0
FIRST_HIT=""
LAST_HIT=""

echo
echo "── Results ──"
echo "  (Only JSON hits and errors are printed; Not Found entries are counted and saved to the TSV.)"
for ver in "${VERSIONS[@]}"; do
  safe="${ver//./_}"
  line="$(cat "$STAT_DIR/${safe}.status" 2>/dev/null || true)"
  IFS=$'\t' read -r req cls http body <<<"$line"
  case "$cls" in
    not_found)
      MISSES=$((MISSES + 1))
      echo -e "${req}\t-\t${http}\tNot Found" >>"$RESULTS_FILE"
      ;;
    json:*)
      offered="${cls#json:}"
      echo "  ${req} -> JSON (offered: ${offered})"
      if [[ -z "$FIRST_HIT" ]]; then FIRST_HIT="$req"; fi
      LAST_HIT="$req"
      HITS=$((HITS + 1))
      echo -e "${req}\t${offered}\t${http}\t${body}" >>"$RESULTS_FILE"
      ;;
    *)
      echo "  ${req} -> OTHER (HTTP ${http}): ${body:0:120}"
      OTHERS=$((OTHERS + 1))
      echo -e "${req}\t-\t${http}\t${body}" >>"$RESULTS_FILE"
      ;;
  esac
done

echo
echo "── Summary ──"
echo "  hits (JSON answers): $HITS"
echo "  misses (Not Found):  $MISSES"
echo "  other (errors):      $OTHERS"
if [[ "$HITS" -gt 0 ]]; then
  echo "  first hit: $FIRST_HIT"
  echo "  last hit:  $LAST_HIT"
  echo "  ➜ The endpoint does answer with data for at least some version strings,"
  echo "    so model + version params can be validated against it."
else
  echo "  ➜ No version string returned JSON. Either the params/model are rejected,"
  echo "    or this endpoint only ever answers 'Not Found' (no-update) for the"
  echo "    supplied identity. Try providing ECO_DID/ECO_SN or a different host."
fi
echo "  Results saved to: $RESULTS_FILE"
echo
echo "🎉 Done!"
