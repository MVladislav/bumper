#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR
# ==============================================================================
# Ecovacs API Sync Script
# Requirements: curl, jq, openssl
# ==============================================================================

# Ensure required env vars
if [[ -z "${ECOVACS_ACCOUNT_ID:-}" || -z "${ECOVACS_PASSWORD:-}" ]]; then
  echo "❌ ERROR: Please set ECOVACS_ACCOUNT_ID and ECOVACS_PASSWORD environment variables." >&2
  exit 1
fi

# Dependency checks
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq required" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl required" >&2; exit 1; }

# --- Configuration ------------------------------------------------------------
ACCOUNT_ID="$ECOVACS_ACCOUNT_ID"
PASSWORD="$ECOVACS_PASSWORD"
LANG="EN"
APP_CODE="global_e"
APP_VERSION="3.14.0"
CHANNEL="${ECO_CHANNEL:-google_play}"
DEVICE_TYPE="1"
REALM="ecouser.net"
ANDROID_MODEL="Pixel 7"
ANDROID_SYSTEM="Android 14"

CLIENT_KEY="1520391301804"
CLIENT_SECRET="6c319b2a5cd3e66e39159c2e28f2fce9" # pragma: allowlist secret gitleaks:allow
AUTH_CLIENT_KEY="1520391491841"
AUTH_CLIENT_SECRET="77ef58ce3afbe337da74aa8c5ab963a9" # pragma: allowlist secret

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
COUNTRIES=("DE" "US" "JP")
LOGIN_COUNTRY="${COUNTRIES[0]}"
meta_params=(
  "lang=$LANG"
  "appCode=$APP_CODE"
  "appVersion=$APP_VERSION"
  "channel=$CHANNEL"
  "deviceType=$DEVICE_TYPE"
  "country=${LOGIN_COUNTRY,,}"
)

TARGET_JSON_PATH="bumper/web/static_api"

# --- Helpers ------------------------------------------------------------------
md5() { echo -n "$1" | openssl dgst -md5 | awk '{print $2}'; }
build_login_signature() {
  local key="$1" secret="$2"
  shift 2
  local params=("$@") sorted signstr
  mapfile -t sorted < <(for kv in "${params[@]}"; do echo "$kv"; done | sort)
  signstr="$key"
  for kv in "${sorted[@]}"; do signstr+="$kv"; done
  signstr+="$secret"
  md5 "$signstr"
}
get_continent_postfix() {
  case "$1" in
  AD | AL | AT | AX | BA | BE | BG | BY | CH | CY | CZ | DE | DK | EE | ES | FI | FO | FR | GB | GG | GI | GR | HR | HU | IE | IM | IS | IT | JE | LI | LT | LU | LV | MC | MD | ME | MK | MT | NL | NO | PL | PT | RO | RS | RU | SE | SI | SJ | SK | SM | UA | VA) echo "-eu" ;;
  AG | AI | AW | BB | BL | BM | BQ | BS | BZ | CA | CR | CU | CW | DM | DO | GD | GL | GP | GT | HN | HT | JM | KN | KY | LC | MF | MQ | MS | MX | NI | PA | PM | PR | SV | SX | TC | TT | US | VC | VG | VI) echo "-na" ;;
  AE | AF | AM | AZ | BD | BH | BN | BT | CC | CX | GE | HK | ID | IL | IN | IO | IQ | IR | JO | JP | KG | KH | KP | KR | KW | KZ | LA | LB | LK | MM | MN | MO | MV | MY | NP | OM | PH | PK | PS | QA | SA | SG | SY | TH | TJ | TM | TR | TW | UZ | VN | YE) echo "-as" ;;
  AO | AQ | AR | AS | AU | BF | BI | BJ | BO | BR | BV | BW | CD | CF | CG | CI | CK | CL | CM | CN | CO | CV | DJ | DZ | EC | EG | EH | ER | ET | FJ | FK | FM | GA | GF | GH | GM | GN | GQ | GS | GU | GW | GY | HM | KE | KI | KM | LR | LS | LY | MA | MG | MH | ML | MP | MR | MU | MW | MZ | NA | NC | NE | NF | NG | NR | NU | NZ | PE | PF | PG | PN | PW | PY | RE | RW | SB | SC | SD | SH | SL | SN | SO | SR | SS | ST | SZ | TD | TF | TG | TK | TL | TN | TO | TV | TZ | UG | UM | UY | VE | VU | WF | WS | YT | ZA | ZM | ZW) echo "-ww" ;;
  *) echo "-ww" ;;
  esac
}
CONTINENT_POSTFIX="$(get_continent_postfix "$LOGIN_COUNTRY")"
timestamp_ms() { echo $(($(date +%s%N) / 1000000)); }
default_curl() {
  local m="$1" u="$2"
  shift 2
  curl -k -sS --connect-timeout 10 --max-time 60 -X "$m" -H "User-Agent: $USER_AGENT" --url "$u" "$@"
}
call_private_api() {
  local endpoint="$1" key="$2" secret="$3"
  shift 3
  local params=("$@")
  local url timestamp request_id sign args resp rc p query_args=()
  timestamp="$(timestamp_ms)"
  request_id="$(md5 "$(date +%s.%N)")"
  args=( "${meta_params[@]}" "deviceId=$DEVICE_ID" "requestId=$request_id" "authTimespan=$timestamp" "authTimeZone=GMT-8" "${params[@]}" )
  sign="$(build_login_signature "$key" "$secret" "${args[@]}")"
  url="https://gl-${LOGIN_COUNTRY,,}-api.ecovacs.com/v1/private/${LOGIN_COUNTRY,,}/${LANG}/${DEVICE_ID}/${APP_CODE}/${APP_VERSION}/${CHANNEL}/${DEVICE_TYPE}/${endpoint}"
  for p in "${params[@]}"; do
    query_args+=( --data-urlencode "$p" )
  done
  resp="$(default_curl GET "$url" --get \
    --data-urlencode "requestId=$request_id" \
    --data-urlencode "authTimespan=$timestamp" \
    --data-urlencode "authTimeZone=GMT-8" \
    "${query_args[@]}" \
    --data-urlencode "authSign=$sign" \
    --data-urlencode "authAppkey=$key")" || rc=$?
  if [[ -n "${rc:-}" ]]; then
    echo "❌ Request to $url failed (curl exit $rc). Check DNS / proxy / firewall." >&2
    exit 1
  fi
  printf '%s' "$resp"
}

# --- Step 1: Login (get accessToken and uid) ----------------------------------
# Device verification flow (Ecovacs returns error 1013 for unverified device IDs)
verify_device() {
  echo "🔐 Step 1b: Device verification required (Ecovacs error 1013)..."
  local pub_key_b64 encrypted email_resp email_code verify_resp verification_code config_resp
  TMP_DIR="$(mktemp -d)"

  echo "  ⬇️  Fetching Ecovacs public key..."
  local config_resp
  config_resp="$(call_private_api "common/getConfig" "$CLIENT_KEY" "$CLIENT_SECRET" "keys=PUBLIC.KEY.CONFIG")"
  pub_key_b64="$(jq -r '.data[] | select(.key == "PUBLIC.KEY.CONFIG") | .value | fromjson | .publicKey // empty' <<<"$config_resp")"
  if [[ -z "$pub_key_b64" ]]; then
    echo "❌ Failed to fetch public key: $config_resp" >&2
    exit 1
  fi

  echo "  🔐 Encrypting account with Ecovacs public key..."
  printf '%s' "$pub_key_b64" | base64 -d >"$TMP_DIR/pub.der"
  openssl pkey -pubin -inform DER -in "$TMP_DIR/pub.der" -out "$TMP_DIR/pub.pem" 2>/dev/null
  encrypted="$(printf '%s' "$ACCOUNT_ID" | openssl pkeyutl -encrypt -pubin -inkey "$TMP_DIR/pub.pem" -pkeyopt rsa_padding_mode:pkcs1 | base64 -w0)"

  echo "  📧 Requesting verification code for '$ACCOUNT_ID'..."
  email_resp="$(call_private_api "user/sendEmailVerifyCode" "$CLIENT_KEY" "$CLIENT_SECRET" \
    "encryptEmail=$encrypted" "verifyType=EMAIL_VERIFY_DEVICE" "supportChar=N" "isForce=N")"
  email_code="$(jq -r '.code // empty' <<<"$email_resp")"
  if [[ "$email_code" != "0000" ]]; then
    echo "❌ sendEmailVerifyCode failed: $email_resp" >&2
    echo "   Note: '0002 Parameter error' after repeated runs usually means Ecovacs is" >&2
    echo "   rate-limiting verification-code requests. Wait 10-30 minutes before retrying." >&2
    echo "   Alternatively try: ECO_CHANNEL=google $0" >&2
    exit 1
  fi

  if [[ -n "${ECO_VERIFY_CODE:-}" ]]; then
    verification_code="$ECO_VERIFY_CODE"
  else
    read -r -p "  📩 Enter the verification code from your email: " verification_code
  fi
  if [[ -z "$verification_code" ]]; then
    echo "❌ No verification code provided." >&2
    exit 1
  fi

  verify_resp="$(call_private_api "user/verifyDevice" "$CLIENT_KEY" "$CLIENT_SECRET" \
    "encryptAccount=$encrypted" "backUpEmail=" "verifyCode=$verification_code" \
    "model=$ANDROID_MODEL" "system=$ANDROID_SYSTEM")"
  ACCESS_TOKEN="$(jq -r '.data.accessToken // empty' <<<"$verify_resp")"
  USER_ID="$(jq -r '.data.uid // empty' <<<"$verify_resp")"
  if [[ -z "$ACCESS_TOKEN" || -z "$USER_ID" ]]; then
    echo "❌ verifyDevice failed: $verify_resp" >&2
    exit 1
  fi
  echo "✅ Device verified. UID: '$USER_ID'"
}

# Stable device ID required: verification is bound to it and it must not change
# across runs. Override with ECO_DEVICE_ID or store in ECO_DEVICE_ID_FILE.
DEVICE_ID_FILE="${ECO_DEVICE_ID_FILE:-.eco-device-id}"
if [[ -n "${ECO_DEVICE_ID:-}" ]]; then
  DEVICE_ID="$ECO_DEVICE_ID"
elif [[ -f "$DEVICE_ID_FILE" ]]; then
  DEVICE_ID="$(<"$DEVICE_ID_FILE")"
else
  DEVICE_ID="$(tr -dc 'A-Z0-9' </dev/urandom | head -c 8 || true)"
  printf '%s\n' "$DEVICE_ID" >"$DEVICE_ID_FILE"
  echo "🔑 Generated new device ID '$DEVICE_ID' (stored in $DEVICE_ID_FILE)"
fi

# Device verification uses a temp dir; clean it up on exit (also on failure).
# TMP_DIR is global because verify_device's locals are gone by the time the
# EXIT trap runs.
TMP_DIR=""
trap 'if [ -n "${TMP_DIR:-}" ]; then rm -rf "$TMP_DIR"; fi' EXIT

echo "🔑 Step 1: Logging in..."
PASSWORD_HASH=$(md5 "$PASSWORD")

login_params=(
  "account=$ACCOUNT_ID"
  "password=$PASSWORD_HASH"
)

LOGIN_JSON=$(call_private_api "user/login" "$CLIENT_KEY" "$CLIENT_SECRET" "${login_params[@]}")
LOGIN_CODE=$(jq -r '.code // empty' <<<"$LOGIN_JSON")

if [[ "$LOGIN_CODE" == "1013" ]]; then
  verify_device
elif [[ "$LOGIN_CODE" != "0000" ]]; then
  echo "❌ Login failed: $LOGIN_JSON" >&2
  exit 1
else
  ACCESS_TOKEN=$(jq -r '.data.accessToken // empty' <<<"$LOGIN_JSON")
  USER_ID=$(jq -r '.data.uid // empty' <<<"$LOGIN_JSON")
  if [[ -z "$ACCESS_TOKEN" || -z "$USER_ID" ]]; then
    echo "❌ Login failed: $LOGIN_JSON" >&2
    exit 1
  fi
  echo "✅ Login successful. UID: '$USER_ID'"
fi

# --- Step 2: Get authCode -----------------------------------------------------
echo "🔐 Step 2: Fetching authCode..."
AUTHCODE_URL="https://gl-${LOGIN_COUNTRY,,}-openapi.ecovacs.com/v1/global/auth/getAuthCode"
AUTH_TIMESTAMP2=$(timestamp_ms)
SIGN_STRING2="${AUTH_CLIENT_KEY}accessToken=${ACCESS_TOKEN}authTimespan=${AUTH_TIMESTAMP2}bizType=ECOVACS_IOTdeviceId=${DEVICE_ID}openId=globaluid=${USER_ID}${AUTH_CLIENT_SECRET}"
AUTH_SIGN2=$(md5 "$SIGN_STRING2")

AUTHCODE_RESP=$(
  default_curl GET "$AUTHCODE_URL" --get \
    --data-urlencode "uid=$USER_ID" \
    --data-urlencode "accessToken=$ACCESS_TOKEN" \
    --data-urlencode "bizType=ECOVACS_IOT" \
    --data-urlencode "deviceId=$DEVICE_ID" \
    --data-urlencode "authTimespan=$AUTH_TIMESTAMP2" \
    --data-urlencode "openId=global" \
    --data-urlencode "authSign=$AUTH_SIGN2" \
    --data-urlencode "authAppkey=$AUTH_CLIENT_KEY"
)

AUTH_CODE=$(jq -r '.data.authCode // empty' <<<"$AUTHCODE_RESP")
if [[ -z "$AUTH_CODE" ]]; then
  echo "❌ AuthCode failed: $AUTHCODE_RESP" >&2
  exit 1
fi

echo "✅ AuthCode: '$AUTH_CODE'"

# --- Step 3: loginByItToken ---------------------------------------------------
echo "🔐 Step 3: Acquiring user token..."
PORTAL_URL="https://portal${CONTINENT_POSTFIX}.ecouser.net/api/users/user.do"
LOGINBYIT_PAYLOAD=$(
  jq -n \
    --arg edition "ECOGLOBLE" \
    --arg userId "$USER_ID" \
    --arg token "$AUTH_CODE" \
    --arg realm "$REALM" \
    --arg resource "$DEVICE_ID" \
    --arg org "ECOWW" \
    --arg last "" \
    --arg country "$LOGIN_COUNTRY" \
    --arg todo "loginByItToken" \
    '{
        edition: $edition,
        userId: $userId,
        token: $token,
        realm: $realm,
        resource: $resource,
        org: $org,
        last: $last,
        country: $country,
        todo: $todo
    }'
)

USER_TOKEN_RESP=$(
  default_curl POST "$PORTAL_URL" \
    -H "Content-Type: application/json" \
    -d "$LOGINBYIT_PAYLOAD"
)

USER_TOKEN=$(jq -r '.token // empty' <<<"$USER_TOKEN_RESP")
if [[ -z "$USER_TOKEN" ]]; then
  echo "❌ loginByItToken failed: $USER_TOKEN_RESP" >&2
  exit 1
fi

echo "✅ User token acquired: '$USER_TOKEN'"

# --- Step 4: Download & combine config files ----------------------------------
echo "📥 Step 4: Downloading config files..."
# API_URL="https://portal${CONTINENT_POSTFIX}.ecouser.net/api"
OUTPUT_FOLDER="json_mappings"
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
