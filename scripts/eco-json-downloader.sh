#!/usr/bin/env bash
set -euo pipefail
# ==============================================================================
# Ecovacs API Sync Script
# Requirements: curl, jq, openssl
# ==============================================================================

# Ensure required env vars
if [[ -z "$ECOVACS_ACCOUNT_ID" || -z "$ECOVACS_PASSWORD" ]]; then
  echo "❌ ERROR: Please set ECOVACS_ACCOUNT_ID and ECOVACS_PASSWORD environment variables." >&2
  exit 1
fi

# --- Configuration ------------------------------------------------------------
ACCOUNT_ID="$ECOVACS_ACCOUNT_ID"
PASSWORD="$ECOVACS_PASSWORD"
DEVICE_ID="$(openssl rand -hex 8)"
LANG="EN"
APP_CODE="global_e"
APP_VERSION="1.6.3"
CHANNEL="google_play"
DEVICE_TYPE="1"
REALM="ecouser.net"

CLIENT_KEY="1520391301804"
CLIENT_SECRET="6c319b2a5cd3e66e39159c2e28f2fce9" # pragma: allowlist secret gitleaks:allow
AUTH_CLIENT_KEY="1520391491841"
AUTH_CLIENT_SECRET="77ef58ce3afbe337da74aa8c5ab963a9" # pragma: allowlist secret

USER_AGENT="Dalvik/2.1.0 (Linux; U; Android 5.1.1; A5010 Build/LMY48Z)"
COUNTRIES=("DE" "US" "JP")
LOGIN_COUNTRY="${COUNTRIES[0]}"

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
  curl -k -s -X "$m" -H "User-Agent: $USER_AGENT" --url "$u" "$@"
}

# --- Step 1: Login (get accessToken and uid) ----------------------------------
echo "🔑 Step 1: Logging in..."
PASSWORD_HASH=$(md5 "$PASSWORD")
AUTH_TIMESTAMP=$(timestamp_ms)
REQUEST_ID=$(md5 "$(date +%s)")

meta_params=(
  "lang=$LANG"
  "appCode=$APP_CODE"
  "appVersion=$APP_VERSION"
  "channel=$CHANNEL"
  "deviceType=$DEVICE_TYPE"
  "country=${LOGIN_COUNTRY,,}"
  "deviceId=$DEVICE_ID"
)
login_params=(
  "account=$ACCOUNT_ID"
  "password=$PASSWORD_HASH"
  "requestId=$REQUEST_ID"
  "authTimespan=$AUTH_TIMESTAMP"
  "authTimeZone=GMT-8"
)

AUTH_SIGN=$(build_login_signature "$CLIENT_KEY" "$CLIENT_SECRET" "${meta_params[@]}" "${login_params[@]}")

LOGIN_URL="https://gl-${LOGIN_COUNTRY,,}-api.ecovacs.com/v1/private/${LOGIN_COUNTRY,,}/${LANG}/${DEVICE_ID}/${APP_CODE}/${APP_VERSION}/${CHANNEL}/${DEVICE_TYPE}/user/login"

LOGIN_JSON=$(
  default_curl GET "$LOGIN_URL" --get \
    --data-urlencode "account=$ACCOUNT_ID" \
    --data-urlencode "password=$PASSWORD_HASH" \
    --data-urlencode "requestId=$REQUEST_ID" \
    --data-urlencode "authTimespan=$AUTH_TIMESTAMP" \
    --data-urlencode "authTimeZone=GMT-8" \
    --data-urlencode "appCode=$APP_CODE" \
    --data-urlencode "appVersion=$APP_VERSION" \
    --data-urlencode "channel=$CHANNEL" \
    --data-urlencode "deviceType=$DEVICE_TYPE" \
    --data-urlencode "country=${LOGIN_COUNTRY,,}" \
    --data-urlencode "lang=$LANG" \
    --data-urlencode "deviceId=$DEVICE_ID" \
    --data-urlencode "authSign=$AUTH_SIGN" \
    --data-urlencode "authAppkey=$CLIENT_KEY"
)

ACCESS_TOKEN=$(jq -r '.data.accessToken // empty' <<<"$LOGIN_JSON")
USER_ID=$(jq -r '.data.uid // empty' <<<"$LOGIN_JSON")

if [[ -z "$ACCESS_TOKEN" || -z "$USER_ID" ]]; then
  echo "❌ Login failed: $LOGIN_JSON" >&2
  exit 1
fi

echo "✅ Login successful. UID: '$USER_ID'"

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

for ENDPOINT in "${!FILES[@]}"; do
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
    default_curl POST "$API_URL/$ENDPOINT" \
      -H "Content-Type: application/json" \
      -d "$BODY" | jq . >"$OUTFILE"
    if jq -e '.code == 0 or .code == "0000"' "$OUTFILE" >/dev/null; then
      jq '.data' "$OUTFILE" >"$OUTFILE.tmp" && mv "$OUTFILE.tmp" "$OUTFILE"
      echo "    🔄 Parsed 'data' for '$COUNTRY_CODE'"
    else
      echo "    ⚠️ Warning: '$OUTFILE' did not return code 0, file left unchanged." >&2
    fi
  done
done

# --- Step 4: Download & combine config files ----------------------------------
echo "🛠️ Step 5: Combining config files..."
for ENDPOINT in "${!FILES[@]}"; do
  OUTBASE="${FILES[$ENDPOINT]}"
  echo "  🔀 Combining JSON '$OUTBASE'"

  COMBINED_FILE="$OUTPUT_FOLDER/${OUTBASE}Combined.json"
  # Find all per-country files for this type
  FILES_TO_COMBINE=()
  for COUNTRY_CODE in "${COUNTRIES[@]}"; do
    FILES_TO_COMBINE+=("$OUTPUT_FOLDER/${OUTBASE}V2-${COUNTRY_CODE}.json")
  done

  if [ ${#FILES_TO_COMBINE[@]} -gt 0 ]; then
    if [[ "$OUTBASE" == "configNetAllResponse" ]]; then
      jq -s 'add | unique_by(.groupId) | sort_by(.groupId)' "${FILES_TO_COMBINE[@]}" "bumper/web/plugins/api/pim/configNetAllResponse.json" >"$COMBINED_FILE"
    elif [[ "$OUTBASE" == "productIotMap" ]]; then
      jq -s 'add | unique_by(.classid) | sort_by(.classid)' "${FILES_TO_COMBINE[@]}" "bumper/web/plugins/api/pim/productIotMap.json" >"$COMBINED_FILE"
    elif [[ "$OUTBASE" == "configGroupsResponse" ]]; then
      jq -s 'add | sort_by(.id) | group_by(.id) | map(.[0]) | sort_by(.id)' "${FILES_TO_COMBINE[@]}" "bumper/web/plugins/api/pim/configGroupsResponse.json" >"$COMBINED_FILE"
    fi
    cp "$COMBINED_FILE" "bumper/web/plugins/api/pim/${OUTBASE}.json"
    echo "    ✅ Combined JSON '$OUTBASE' :: copied JSON: '$COMBINED_FILE' -> 'bumper/web/plugins/api/pim/${OUTBASE}.json'"
  fi
done

echo "🎉 Done! Files saved in '$OUTPUT_FOLDER'"
