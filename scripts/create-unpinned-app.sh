#!/usr/bin/env bash
#
# Prepare the Ecovacs app (com.eco.global.app) to talk to Bumper.
#
# Everything runs in a container: the download, the XAPK unpack, both patches,
# zipalign, signing and verification. The host needs nothing but docker, and the
# only thing written outside the container is data/<app-name>/ with the finished
# APKs and certs/bumper-apk.jks.
#
# Two patches, both required:
#
# 1. android:debuggable="true" in the manifest (patch_debuggable.py).
#
#    The app ships this in its network_security_config.xml:
#
#        <debug-overrides>
#            <trust-anchors><certificates src="user"/></trust-anchors>
#        </debug-overrides>
#
#    Android applies <debug-overrides> to every domain, but only to a debuggable
#    app. That one flag is what lets Bumper's user-installed CA be accepted on
#    the web API, CodePush and H5 paths.
#
# 2. The hardcoded MQTT certificate is made unusable (patch_mqtt_trust.py).
#
#    MQTT does not use the platform trust store. The Paho fork loads a Base64
#    certificate embedded in a classes*.dex into an empty KeyStore and passes it
#    to TrustManagerFactory.init(), which replaces the platform store entirely,
#    so the handshake fails with "Trust anchor for certification path not found".
#    The patch keeps a prefix of that string - enough for the dex string_ids
#    table to stay sorted, which ART verifies - so generateCertificate throws,
#    the app's factory returns null, and Paho falls back to null trust managers,
#    i.e. the platform store. Every robot command is relayed over MQTT, so
#    without this patch no command reaches a robot.
#
# Writes installable APKs; it does not install anything.
#
# Requirements: docker
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_DIR="${REPO_ROOT}/scripts/apk-patch"
TOOL_IMAGE='bumper-apk-tool'

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CURL_USER_AGENT='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0'

# One APK URL. XAPK (multi-split) and plain APK both work.
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest' # >= 3.16.0
APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=139&nc=arm64-v8a'  # 3.15.1
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=129&nc=armeabi-v7a' # 3.11.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=128&nc=armeabi-v7a' # 3.10.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=127&nc=arm64-v8a'  # 3.9.1
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=126&nc=arm64-v8a'  # 3.9.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=124&nc=arm64-v8a'  # 3.8.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=123&nc=arm64-v8a'  # 3.7.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=121&nc=arm64-v8a'  # 3.6.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=120&nc=arm64-v8a'  # 3.5.0
# APK_URL='https://d.apkpure.net/b/APK/com.eco.global.app?versionCode=87&nc=arm64-v8a'   # 2.4.1

# Signing key, kept in the repo's certs/ and reused across runs.
SIGNING_KEY="${REPO_ROOT}/certs/bumper-apk.jks"
SIGNING_ALIAS='bumper'
SIGNING_PASS="${SIGNING_PASS:-bumper}"

# SKIP_MQTT_CA=1 builds an app that reaches the web API but never a robot.
SKIP_MQTT_CA="${SKIP_MQTT_CA:-0}"

# Mounted into the container; the finished APKs land in data/<app-name>/.
DATA_DIR="${REPO_ROOT}/data"
KEYS_DIR="${REPO_ROOT}/certs"

# ─── PREREQS ─────────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || { echo "❌ docker not found"; exit 1; }
[[ -f "${PATCH_DIR}/Dockerfile" ]] || { echo "❌ ${PATCH_DIR}/Dockerfile not found"; exit 1; }
docker info >/dev/null 2>&1 || { echo "❌ docker is not running, or you cannot talk to it"; exit 1; }

mkdir -p "${DATA_DIR}" "${KEYS_DIR}"

# ─── TOOLCHAIN IMAGE ─────────────────────────────────────────────────────────
# JDK + Android build-tools + python3 + curl/unzip, plus this directory's
# patchers. Rebuilds only the last layer when a patcher changes.
echo "💡 Preparing the APK toolchain image (bumper-apk-tool)..."
docker build -q -t "${TOOL_IMAGE}" "${PATCH_DIR}"

# ─── RUN ─────────────────────────────────────────────────────────────────────
echo "💡 Building the APKs in a container..."
docker run --rm \
  -v "${DATA_DIR}:/out" \
  -v "${KEYS_DIR}:/keys" \
  -e APK_URL="${APK_URL}" \
  -e CURL_USER_AGENT="${CURL_USER_AGENT}" \
  -e SKIP_MQTT_CA="${SKIP_MQTT_CA}" \
  -e KS_FILE="/keys/$(basename "${SIGNING_KEY}")" \
  -e KS_ALIAS="${SIGNING_ALIAS}" \
  -e KS_PASS="${SIGNING_PASS}" \
  -e OUT_HOST="${DATA_DIR}" \
  "${TOOL_IMAGE}"

# The APKs and the keystore are written by root inside the container.
chmod -R o+rw "${DATA_DIR}" 2>/dev/null || true
chmod o+rw "${SIGNING_KEY}" 2>/dev/null || true
