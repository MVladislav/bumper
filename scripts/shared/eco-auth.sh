#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR
# ==============================================================================
# Ecovacs API authentication Script
# Requirements: curl, jq, openssl
# ==============================================================================
# Source this file and call `eco_login`. On success it sets ACCESS_TOKEN,
# USER_ID and USER_TOKEN. The helpers are used by the update-eco-*.sh scripts.

# Ensure required env vars
if [[ -z "${ECOVACS_ACCOUNT_ID:-}" || -z "${ECOVACS_PASSWORD:-}" ]]; then
  echo "❌ ERROR: Please set ECOVACS_ACCOUNT_ID and ECOVACS_PASSWORD environment variables." >&2
  return 1
fi

# Dependency checks
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl required" >&2; return 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq required" >&2; return 1; }
command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl required" >&2; return 1; }

# --- Configuration ------------------------------------------------------------
LANG="EN"
CLIENT_KEY="1520391301804"
CLIENT_SECRET="6c319b2a5cd3e66e39159c2e28f2fce9" # pragma: allowlist secret gitleaks:allow
AUTH_CLIENT_KEY="1520391491841"
AUTH_CLIENT_SECRET="77ef58ce3afbe337da74aa8c5ab963a9" # pragma: allowlist secret
USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
APP_CODE="global_e"
APP_VERSION="3.14.0"
CHANNEL="${ECO_CHANNEL:-google_play}"
DEVICE_TYPE="1"
REALM="ecouser.net"
ANDROID_MODEL="Pixel 7"
ANDROID_SYSTEM="Android 14"

# The country the account lives in. Callers may set it before `eco_login`.
COUNTRIES=("DE" "US" "JP")
LOGIN_COUNTRY="${COUNTRIES[0]}"

# The credentials of the Ecovacs account.
ACCOUNT_ID="${ECOVACS_ACCOUNT_ID:-}"
PASSWORD="${ECOVACS_PASSWORD:-}"

# Temporary directory of the running script, removed on exit.
TMP_DIR=""

# --- Helpers ------------------------------------------------------------------
md5() { echo -n "$1" | openssl dgst -md5 | awk '{print $2}'; }
md5_file() { openssl dgst -md5 "$1" | awk '{print $2}'; }
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
  meta_params=(
    "lang=$LANG"
    "appCode=$APP_CODE"
    "appVersion=$APP_VERSION"
    "channel=$CHANNEL"
    "deviceType=$DEVICE_TYPE"
    "country=${LOGIN_COUNTRY,,}"
  )
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
    return 1
  fi
  printf '%s' "$resp"
}

# --- Device verification -------------------------------------------------------
# Fetch the verification code by mail and exchange it for an access token.
verify_device() {
  echo "🔐 Step 1b: Device verification required (Ecovacs error 1013)..."
  local pub_key_b64 encrypted email_resp email_code verify_resp verification_code
  TMP_DIR="$(mktemp -d)"

  echo "  ⬇️  Fetching Ecovacs public key..."
  local config_resp
  config_resp="$(call_private_api "common/getConfig" "$CLIENT_KEY" "$CLIENT_SECRET" "keys=PUBLIC.KEY.CONFIG")" || return 1
  pub_key_b64="$(jq -r '.data[] | select(.key == "PUBLIC.KEY.CONFIG") | .value | fromjson | .publicKey // empty' <<<"$config_resp")"
  if [[ -z "$pub_key_b64" ]]; then
    echo "❌ Failed to fetch public key: $config_resp" >&2
    return 1
  fi

  echo "  🔐 Encrypting account with Ecovacs public key..."
  printf '%s' "$pub_key_b64" | base64 -d >"$TMP_DIR/pub.der"
  openssl pkey -pubin -inform DER -in "$TMP_DIR/pub.der" -out "$TMP_DIR/pub.pem" 2>/dev/null
  encrypted="$(printf '%s' "$ACCOUNT_ID" | openssl pkeyutl -encrypt -pubin -inkey "$TMP_DIR/pub.pem" -pkeyopt rsa_padding_mode:pkcs1 | base64 -w0)"

  echo "  📧 Requesting verification code for '$ACCOUNT_ID'..."
  email_resp="$(call_private_api "user/sendEmailVerifyCode" "$CLIENT_KEY" "$CLIENT_SECRET" \
    "encryptEmail=$encrypted" "verifyType=EMAIL_VERIFY_DEVICE" "supportChar=N" "isForce=N")" || return 1
  email_code="$(jq -r '.code // empty' <<<"$email_resp")"
  if [[ "$email_code" != "0000" ]]; then
    echo "❌ sendEmailVerifyCode failed: $email_resp" >&2
    echo "   Note: '0002 Parameter error' after repeated runs usually means Ecovacs is" >&2
    echo "   rate-limiting verification-code requests. Wait 10-30 minutes before retrying." >&2
    echo "   Alternatively try: ECO_CHANNEL=google $0" >&2
    return 1
  fi

  if [[ -n "${ECO_VERIFY_CODE:-}" ]]; then
    verification_code="$ECO_VERIFY_CODE"
  else
    read -r -p "  📩 Enter the verification code from your email: " verification_code
  fi
  if [[ -z "$verification_code" ]]; then
    echo "❌ No verification code provided." >&2
    return 1
  fi

  verify_resp="$(call_private_api "user/verifyDevice" "$CLIENT_KEY" "$CLIENT_SECRET" \
    "encryptAccount=$encrypted" "backUpEmail=" "verifyCode=$verification_code" \
    "model=$ANDROID_MODEL" "system=$ANDROID_SYSTEM")" || return 1
  ACCESS_TOKEN="$(jq -r '.data.accessToken // empty' <<<"$verify_resp")"
  USER_ID="$(jq -r '.data.uid // empty' <<<"$verify_resp")"
  if [[ -z "$ACCESS_TOKEN" || -z "$USER_ID" ]]; then
    echo "❌ verifyDevice failed: $verify_resp" >&2
    return 1
  fi
  echo "✅ Device verified. UID: '$USER_ID'"
}

# --- Login ---------------------------------------------------------------------
# Log in and fetch a user token. Sets ACCESS_TOKEN, USER_ID and USER_TOKEN.
eco_login() {
  # Stable device ID required: verification is bound to it and it must not change
  # across runs. Override with ECO_DEVICE_ID or store in ECO_DEVICE_ID_FILE.
  local device_id_file
  device_id_file="$(abspath "${ECO_DEVICE_ID_FILE:-.eco-device-id}")"
  if [[ -n "${ECO_DEVICE_ID:-}" ]]; then
    DEVICE_ID="$ECO_DEVICE_ID"
  elif [[ -f "$device_id_file" ]]; then
    DEVICE_ID="$(<"$device_id_file")"
  else
    DEVICE_ID="$(tr -dc 'A-Z0-9' </dev/urandom | head -c 8 || true)"
    printf '%s\n' "$DEVICE_ID" >"$device_id_file"
    echo "🔑 Generated new device ID '$DEVICE_ID' (stored in $device_id_file)"
  fi

  echo "🔑 Step 1: Logging in..."
  local password_hash
  password_hash=$(md5 "$PASSWORD")
  local login_params=(
    "account=$ACCOUNT_ID"
    "password=$password_hash"
  )

  local login_json login_code
  login_json=$(call_private_api "user/login" "$CLIENT_KEY" "$CLIENT_SECRET" "${login_params[@]}") || return 1
  login_code=$(jq -r '.code // empty' <<<"$login_json")

  if [[ "$login_code" == "1013" ]]; then
    verify_device || return 1
  elif [[ "$login_code" != "0000" ]]; then
    echo "❌ Login failed: $login_json" >&2
    return 1
  else
    ACCESS_TOKEN=$(jq -r '.data.accessToken // empty' <<<"$login_json")
    USER_ID=$(jq -r '.data.uid // empty' <<<"$login_json")
    if [[ -z "$ACCESS_TOKEN" || -z "$USER_ID" ]]; then
      echo "❌ Login failed: $login_json" >&2
      return 1
    fi
    echo "✅ Login successful. UID: '$USER_ID'"
  fi

  echo "🔐 Step 2: Fetching authCode..."
  local authcode_url auth_timestamp2 sign_string2 auth_sign2 authcode_resp auth_code
  authcode_url="https://gl-${LOGIN_COUNTRY,,}-openapi.ecovacs.com/v1/global/auth/getAuthCode"
  auth_timestamp2=$(timestamp_ms)
  sign_string2="${AUTH_CLIENT_KEY}accessToken=${ACCESS_TOKEN}authTimespan=${auth_timestamp2}bizType=ECOVACS_IOTdeviceId=${DEVICE_ID}openId=globaluid=${USER_ID}${AUTH_CLIENT_SECRET}"
  auth_sign2=$(md5 "$sign_string2")

  authcode_resp=$(
    default_curl GET "$authcode_url" --get \
      --data-urlencode "uid=$USER_ID" \
      --data-urlencode "accessToken=$ACCESS_TOKEN" \
      --data-urlencode "bizType=ECOVACS_IOT" \
      --data-urlencode "deviceId=$DEVICE_ID" \
      --data-urlencode "authTimespan=$auth_timestamp2" \
      --data-urlencode "openId=global" \
      --data-urlencode "authSign=$auth_sign2" \
      --data-urlencode "authAppkey=$AUTH_CLIENT_KEY"
  ) || return 1

  auth_code=$(jq -r '.data.authCode // empty' <<<"$authcode_resp")
  if [[ -z "$auth_code" ]]; then
    echo "❌ AuthCode failed: $authcode_resp" >&2
    return 1
  fi
  echo "✅ AuthCode: '$auth_code'"

  echo "🔐 Step 3: Acquiring user token..."
  local continent_postfix portal_url loginbyit_payload user_token_resp
  continent_postfix="$(get_continent_postfix "$LOGIN_COUNTRY")"
  portal_url="https://portal${continent_postfix}.ecouser.net/api/users/user.do"
  loginbyit_payload=$(
    jq -n \
      --arg edition "ECOGLOBLE" \
      --arg userId "$USER_ID" \
      --arg token "$auth_code" \
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

  user_token_resp=$(
    default_curl POST "$portal_url" \
      -H "Content-Type: application/json" \
      -d "$loginbyit_payload"
  ) || return 1

  USER_TOKEN=$(jq -r '.token // empty' <<<"$user_token_resp")
  if [[ -z "$USER_TOKEN" ]]; then
    echo "❌ loginByItToken failed: $user_token_resp" >&2
    return 1
  fi
  echo "✅ User token acquired"
  return 0
}

# --- Cleanup -------------------------------------------------------------------
# Remove the temporary directory of the running script.
eco_cleanup() {
  if [[ -n "${TMP_DIR:-}" ]]; then
    rm -rf "$TMP_DIR"
    TMP_DIR=""
  fi
}
