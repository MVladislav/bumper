#!/usr/bin/env bash
# ==============================================================================
# Ecovacs Time Zone Sync Script
#
# Fetches the time zones the app shows, with their name in every language, and
# writes them to bumper/web/static_api/timezones.json.
#
# The time zones are the same for every user, but the api wants a login.
#
# Run it before the DNS override is in place, or from a machine that can still
# reach the Ecovacs cloud - the DNS change points the cloud names at Bumper.
#
# Requirements: curl, jq, openssl
# ==============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/shared/paths.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/shared/eco-auth.sh"

# Dependency checks
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl required" >&2; exit 1; }

# --- Configuration ------------------------------------------------------------
# The host of the api in the region the account belongs to.
API_BASE_HOST="${API_BASE_HOST:-api-base.dc-eu.ww.ecouser.net}"
# The country and the language the answer is asked for.
COUNTRY="${LOGIN_COUNTRY:-DE}"
LANG_CODE="${ECO_LANG:-en}"
TARGET_JSON_PATH="$REPO_ROOT/bumper/web/static_api"

# --- Login --------------------------------------------------------------------
eco_login || exit 1

# --- Fetch --------------------------------------------------------------------
# The api checks the signature of the request, it is the md5 of the secret and
# the time of the request.
timestamp="$(timestamp_ms)"
sign="$(printf '%s' "ecovacs2ea31cf06e6711eaa0aff7b9558a534e${timestamp}" | openssl dgst -md5 | awk '{print $NF}')"

url="https://${API_BASE_HOST}/api/basis/time/timezones?sort=asc"
echo "==> Fetching the time zones from ${url}"
response="$(default_curl GET "$url" \
  -H "Accept: application/json" \
  -H "appid: ecovacs" \
  -H "plat: android" \
  -H "ts: ${timestamp}" \
  -H "country: ${COUNTRY}" \
  -H "lang: ${LANG_CODE}" \
  -H "v: ${APP_VERSION}" \
  -H "sign: ${sign}" \
  -H "token: ${USER_TOKEN}" \
  -H "userid: ${USER_ID}" \
  -H "authorization: ${USER_TOKEN}")" || exit 1

data="$(jq -c '.data // empty' <<<"$response")"
if [[ -z "$data" ]]; then
  echo "[ERROR] The api did not answer with the time zones:" >&2
  echo "$response" >&2
  exit 1
fi

# The output is sorted by the time zone and one entry per line, so a re-run does
# not produce a noisy diff. The order of the fields is the one of the api.
{
  printf '[\n'
  jq -c 'sort_by(.code) | .[]' <<<"$data" | sed -e '$!s/$/,/' -e 's/^/  /'
  printf ']\n'
} >"$TARGET_JSON_PATH/timezones.json"
echo "==> Wrote $(jq 'length' <<<"$data") time zones to ${TARGET_JSON_PATH}/timezones.json"
