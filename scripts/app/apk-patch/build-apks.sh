#!/usr/bin/env bash
#
# In-container APK pipeline: download, unpack, patch, align, sign, verify.
# Runs as the image's entrypoint; scripts/app/create-unpinned-app.sh starts it and
# passes the settings below as environment variables.
#
# Mounts expected:
#   /out    the repo's data/ directory; the finished APKs are written to
#           /out/<app-name>/
#   /keys   the repo's certs/ directory; holds the signing keystore
#
# The download, the unpacked splits and the intermediate aligned copies all stay
# in the container's own filesystem and go away with it.
set -Eeuo pipefail

PATCH_DIR=/opt/apk-patch
WORK=/work
OUT=/out
KEYS=/keys

APK_URL="${APK_URL:?APK_URL is required}"
CURL_USER_AGENT="${CURL_USER_AGENT:?CURL_USER_AGENT is required}"
KS_ALIAS="${KS_ALIAS:?KS_ALIAS is required}"
KS_PASS="${KS_PASS:?KS_PASS is required}"
OUT_HOST="${OUT_HOST:?OUT_HOST is required}"
SKIP_MQTT_CA="${SKIP_MQTT_CA:-0}"
KS_FILE="${KS_FILE:-${KEYS}/bumper-apk.jks}"

fail() {
  echo "❌ $*" >&2
  exit 1
}

# ─── SIGNING KEY ─────────────────────────────────────────────────────────────
# Created once and reused: Android rejects an update signed with a different key,
# which would clear the logged-in account on every re-patch.
if [[ -f "${KS_FILE}" ]]; then
  echo "💡 Reusing signing key: ${KS_FILE}"
else
  echo "💡 Creating signing key (reused on future runs)..."
  keytool -genkeypair \
    -keystore "${KS_FILE}" \
    -storepass "${KS_PASS}" -keypass "${KS_PASS}" \
    -alias "${KS_ALIAS}" -keyalg RSA -keysize 4096 -validity 10000 \
    -dname 'CN=Bumper, O=ecovacs, C=US' >/dev/null
  [[ -f "${KS_FILE}" ]] || fail "failed to create the signing key"
fi

# ─── DOWNLOAD ────────────────────────────────────────────────────────────────
echo "💡 Resolving download..."
APK_NAME="$(curl -H "User-Agent: ${CURL_USER_AGENT}" -sI -L "${APK_URL}" \
  | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
[[ -n "${APK_NAME}" ]] || fail "could not determine the filename from ${APK_URL}"
APK_BASENAME="${APK_NAME%.*}"
APK_EXTENSION="${APK_NAME##*.}"
echo "   - ${APK_NAME}"

mkdir -p "${WORK}"
echo "💡 Downloading..."
curl -H "User-Agent: ${CURL_USER_AGENT}" -sSL "${APK_URL}" -o "${WORK}/${APK_NAME}"

# ─── EXTRACT SPLITS ──────────────────────────────────────────────────────────
# Extract into WORK and delete the archive, so peak usage does not hold the
# XAPK and its contents at once.
if [[ "${APK_EXTENSION}" == "xapk" ]]; then
  echo "💡 Extracting XAPK splits..."
  unzip -qo "${WORK}/${APK_NAME}" -d "${WORK}"
  rm -f "${WORK}/${APK_NAME}"
else
  mv "${WORK}/${APK_NAME}" "${WORK}/base.apk"
fi
shopt -s nullglob
splits=("${WORK}"/*.apk)
[[ ${#splits[@]} -gt 0 ]] || fail "no .apk found in the download"
echo "   - ${#splits[@]} split(s)"

# ─── PATCH ───────────────────────────────────────────────────────────────────
# Only the base split has an <application> element, and it is by far the largest
# split, so select on size.
BASE_APK="$(ls -S "${WORK}"/*.apk | head -n1)"
echo "💡 Base split: $(basename "${BASE_APK}")"

echo "💡 Setting android:debuggable=true (this is what makes Bumper's CA trusted)..."
python3 "${PATCH_DIR}/patch-debuggable.py" "${BASE_APK}" "${WORK}/base.debuggable" --force
mv -f "${WORK}/base.debuggable" "${BASE_APK}"

if [[ "${SKIP_MQTT_CA}" == "1" ]]; then
  echo "⚠️  SKIP_MQTT_CA=1 - leaving Ecovacs' pinned MQTT certificate in place."
  echo "   The web API will work; every robot command will time out."
else
  echo "💡 Making MQTT use the platform trust store (it pins its own certificate)..."
  python3 "${PATCH_DIR}/patch-mqtt-trust.py" "${BASE_APK}" "${WORK}/base.mqtt" --force
  mv -f "${WORK}/base.mqtt" "${BASE_APK}"
fi

# ─── ALIGN + SIGN ────────────────────────────────────────────────────────────
OUT_DIR="${OUT}/${APK_BASENAME}"
mkdir -p "${OUT_DIR}"
rm -f "${OUT_DIR}"/*.apk

echo "💡 Aligning and signing..."
for apk in "${WORK}"/*.apk; do
  name="$(basename "${apk}")"
  # zipalign needs a distinct output file; drop it after signing.
  zipalign -f -p 4 "${apk}" "${WORK}/${name}.aligned"
  # v1 and v2 are requested explicitly so older app versions in the APK_URL list
  # work too; apksigner settles on v3 for a minSdk 32 build regardless.
  java -jar /opt/build-tools/apksigner.jar sign \
    --ks "${KS_FILE}" --ks-key-alias "${KS_ALIAS}" \
    --ks-pass "pass:${KS_PASS}" --key-pass "pass:${KS_PASS}" \
    --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
    --out "${OUT_DIR}/${name}" "${WORK}/${name}.aligned"
  rm -f "${WORK}/${name}.aligned"
  echo "   signed ${name}"
done

# ─── VERIFY ──────────────────────────────────────────────────────────────────
echo "💡 Verifying..."
python3 "${PATCH_DIR}/verify-apks.py" "${OUT_DIR}"

# ─── RESULT ──────────────────────────────────────────────────────────────────
HOST_OUT_DIR="${OUT_HOST}/${APK_BASENAME}"
echo
echo "✅ Done. Installable APKs are in: ${HOST_OUT_DIR}"
echo
echo "   Install with:"
if [[ ${#splits[@]} -gt 1 ]]; then
  echo "     adb install-multiple --no-incremental ${HOST_OUT_DIR}/*.apk"
else
  echo "     adb install --no-incremental ${HOST_OUT_DIR}/*.apk"
fi
echo
echo "   Then install Bumper's CA on the phone as a USER certificate:"
echo "     certs/ca.crt   (Settings → Security → Encryption & credentials →"
echo "                   Install a certificate → CA certificate)"
echo
echo "   Notes:"
echo "     • Re-signing changes the app's signature, so the first install replaces"
echo "       any existing copy and clears its data (re-login needed). Afterwards"
echo "       keep ${KS_FILE##*/} so upgrades keep your session."
echo "     • MQTT uses the Android trust store like every other channel, so"
echo "       Bumper's user-installed CA is what it validates against."
if [[ "${SKIP_MQTT_CA}" == "1" ]]; then
  echo "     • SKIP_MQTT_CA was set: robot control over MQTT will NOT work."
fi
echo "     • A white login screen on an emulator is expected - the app needs an"
echo "       arm64 device (or an arm64 system image) to find libhermes.so."
