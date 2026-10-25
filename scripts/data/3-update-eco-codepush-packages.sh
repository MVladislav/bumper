#!/usr/bin/env bash
set -euo pipefail
trap 'echo "ERROR: Unexpected error on line $LINENO (command: $BASH_COMMAND)." >&2' ERR
# ==============================================================================
# Ecovacs CodePush Package Sync Script
#
# Downloads the CodePush packages the app can update to, so that Bumper can
# serve them instead of the cloud. The packages are a few MB to a few dozen MB
# each and are NOT part of the repository: they land in the CodePush directory
# (BUMPER_CODEPUSH) and the user has to run this script before the server
# starts if the app should be able to update.
#
# The urls, the hashes and the sizes come from
# bumper/web/static_api/updateCheck.json, which `1-update-eco-codepush.sh`
# refreshes from the cloud.
#
# Set CODEPUSH_LOCAL_PACKAGE to true to make the app download the package
# from Bumper instead of from the cloud. The download url then names the
# host of the CodePush service, which has to be one that the DNS override
# points at Bumper.
#
# Run it before the DNS override is in place, or from a machine that can still
# reach the Ecovacs cloud - the DNS change points the cloud names at Bumper.
#
# Requirements: curl, jq, sha256sum
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../shared/paths.sh"

# Dependency checks
command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq required" >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "[ERROR] sha256sum required" >&2; exit 1; }

# --- Configuration ------------------------------------------------------------
# The paths are absolute, so the script writes to the same place no matter
# which directory it is run from.
CODEPUSH_DIR="$(abspath "${BUMPER_CODEPUSH:-${BUMPER_DATA:-$REPO_ROOT/data}/codepush}")"
UPDATE_CHECK_FILE="$REPO_ROOT/bumper/web/static_api/updateCheck.json"
# The deployments to fetch, comma separated. Empty means every deployment the
# cloud offers. A deployment is one key of the app, and every key has its own
# package.
DEPLOYMENT_KEYS="${CODEPUSH_DEPLOYMENT_KEYS:-}"
# Set to 1 to download the packages again, even when they are there.
FORCE="${CODEPUSH_FORCE:-0}"
# How many packages are downloaded at the same time.
PARALLEL="${ECO_PARALLEL:-4}"

if [[ ! -f "$UPDATE_CHECK_FILE" ]]; then
  echo "[ERROR] No update check file at '$UPDATE_CHECK_FILE'" >&2
  exit 1
fi

# --- Step 1: The deployments the cloud offers ---------------------------------
echo "📋 Step 1: Reading the deployments..."
mapfile -t ALL_KEYS < <(jq -r 'keys[]' "$UPDATE_CHECK_FILE")
if [[ ${#ALL_KEYS[@]} -eq 0 ]]; then
  echo "[ERROR] No deployment in '$UPDATE_CHECK_FILE'" >&2
  exit 1
fi

if [[ -n "$DEPLOYMENT_KEYS" ]]; then
  KEYS=()
  IFS=',' read -r -a REQUESTED <<<"$DEPLOYMENT_KEYS"
  for KEY in "${REQUESTED[@]}"; do
    KEY="$(tr -d '[:space:]' <<<"$KEY")"
    [[ -z "$KEY" ]] && continue
    if ! printf '%s\n' "${ALL_KEYS[@]}" | grep -qxF "$KEY"; then
      echo "[ERROR] Unknown deployment key '$KEY'" >&2
      exit 1
    fi
    KEYS+=("$KEY")
  done
else
  KEYS=("${ALL_KEYS[@]}")
fi
echo "  🗂️  Deployments: ${#KEYS[@]}"

# --- Step 2: The package of every deployment ---------------------------------
# The packages are big, so they are fetched at the same time. Every worker
# writes a status file, named after the deployment, so that the report can
# tell the deployments that are stored from the ones that are not.
echo "📥 Step 2: Downloading the packages..."
mkdir -p "$CODEPUSH_DIR"
TMP_DIR="$(mktemp -d)"
STAT_DIR="$TMP_DIR/status"
mkdir -p "$STAT_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

mark() { printf '%s\n' "$2" >"$STAT_DIR/$1"; }

# Download the package of one deployment. The status is written to a file, so
# that the workers do not write to the same place.
process_key() {
  local key="$1" url hash size target tmp_file local_size

  url="$(jq -r --arg dk "$key" '.[$dk].update_info.download_url // ""' "$UPDATE_CHECK_FILE")"
  hash="$(jq -r --arg dk "$key" '.[$dk].update_info.package_hash // ""' "$UPDATE_CHECK_FILE")"
  size="$(jq -r --arg dk "$key" '.[$dk].update_info.package_size // 0' "$UPDATE_CHECK_FILE")"

  if [[ -z "$url" ]]; then
    echo "  ⚠️ '$key': no download url"
    mark "$key" skipped
    return 0
  fi

  target="$CODEPUSH_DIR/$key"

  # A package that is already there and has the right size is kept. The hash
  # of the deployment is the name the app gives the package, not the
  # checksum of the file, so the size is what is checked.
  if [[ "$FORCE" != "1" && -f "$target" ]]; then
    if [[ "$size" == "0" ]] || [[ "$(stat -c%s "$target")" == "$size" ]]; then
      echo "  ✔️ '$key': already there"
      mark "$key" ok
      return 0
    fi
    echo "  ♻️ '$key': the size does not match, downloading again"
  fi

  echo "  ⬇️ '$key': ${size} bytes"
  tmp_file="$(mktemp)"
  if ! curl -k -sSfL --connect-timeout 10 --max-time 900 -o "$tmp_file" "$url"; then
    echo "    ❌ Download failed for '$key'" >&2
    rm -f "$tmp_file"
    mark "$key" failed
    return 0
  fi

  # A file that is not the size of the package is not the package.
  if [[ "$size" != "0" ]]; then
    local_size="$(stat -c%s "$tmp_file")"
    if [[ "$local_size" != "$size" ]]; then
      echo "    ❌ Size mismatch for '$key': expected '$size', got '$local_size'" >&2
      rm -f "$tmp_file"
      mark "$key" failed
      return 0
    fi
  fi

  mv "$tmp_file" "$target"
  echo "    ✅ '$key' stored (sha256 $(sha256sum "$target" | cut -d' ' -f1), hash of the deployment $hash)"
  mark "$key" ok
}
export -f process_key mark
export CODEPUSH_DIR UPDATE_CHECK_FILE STAT_DIR FORCE

echo "----------------------------------------"
printf '%s\n' "${KEYS[@]}" | xargs -P "$PARALLEL" -n 1 bash -c 'process_key "$@"' _
echo "----------------------------------------"

# --- Step 3: Report ------------------------------------------------------------
echo "📊 Step 3: Done."
echo "  📁 Packages in '$CODEPUSH_DIR'"

FAILED_KEYS=()
SKIPPED_KEYS=()
for KEY in "${KEYS[@]}"; do
  case "$(cat "$STAT_DIR/$KEY" 2>/dev/null || echo failed)" in
    ok) ;;
    skipped) SKIPPED_KEYS+=("$KEY") ;;
    *) FAILED_KEYS+=("$KEY") ;;
  esac
done

if [[ ${#SKIPPED_KEYS[@]} -gt 0 ]]; then
  echo "  ⚠️ Without a package: ${SKIPPED_KEYS[*]}"
fi

if [[ ${#FAILED_KEYS[@]} -gt 0 ]]; then
  echo "  ❌ Failed: ${FAILED_KEYS[*]}" >&2
  exit 1
fi

echo "🎉 Done! Start Bumper with"
echo "   BUMPER_CODEPUSH='$CODEPUSH_DIR'"
echo "   CODEPUSH_LOCAL_PACKAGE=true"
echo "to serve the packages from here."
