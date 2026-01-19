#!/usr/bin/env bash
set -Eeuo pipefail

# ─── PREREQS ─────────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || {
  echo "❌ docker not found"
  exit 1
}

# ─── TRAP ────────────────────────────────────────────────────────────────────
WORKDIR="$(mktemp -d)"
echo "📁 Working in: $WORKDIR"
cleanup() {
  local exit_code=$?
  if [[ $exit_code -ne 0 ]]; then
    echo -e "⚠️  Script failed with exit code $exit_code"
    echo -e "❌  Last command: '$BASH_COMMAND'"
  else
    echo -e "✅  Script finished successfully."
  fi
  rm -rf "$WORKDIR"
}
trap cleanup EXIT
trap 'echo -e "\n🛑  Script interrupted."; exit 130' INT TERM

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CURL_USER_AGENT='Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0'
IMAGE='node:25-slim'
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest' # >= 3.9.1
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=127&nc=arm64-v8a' # 3.9.1
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=126&nc=arm64-v8a' # 3.9.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=124&nc=arm64-v8a' # 3.8.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=123&nc=arm64-v8a' # 3.7.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=121&nc=arm64-v8a' # 3.6.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=120&nc=arm64-v8a' # 3.5.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=119&nc=arm64-v8a' # 3.4.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=117&nc=arm64-v8a' # 3.3.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=109&nc=arm64-v8a' # 3.0.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=107&nc=arm64-v8a' # 2.5.9
APK_URL='https://d.apkpure.net/b/APK/com.eco.global.app?versionCode=87&nc=arm64-v8a' # 2.4.1
echo "💡 Collecting base information..."
APK_NAME="$(curl -H "User-Agent: ${CURL_USER_AGENT}" -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
APK_BASENAME="${APK_NAME%.*}"
APK_EXTENSION="${APK_NAME##*.}"
PATCHED_NAME="${APK_BASENAME}-patched.${APK_EXTENSION}"
CERT_PATH="$(pwd)/certs/ca.crt"
[ -f "$CERT_PATH" ] || {
  echo "❌ Certificate not found at $CERT_PATH"
  exit 1
}

# ─── BUILD TEMP IMAGE ────────────────────────────────────────────────────────
echo "💡 Building Docker image..."
docker build --pull --rm -q -t apk-mitm-unpin - <<EOF
FROM ${IMAGE}
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openjdk-17-jre-headless curl zip unzip \
 && npm install -g apk-mitm \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /work
ENTRYPOINT ["sh","-c"]
EOF

# ─── RUN DOWNLOAD + UNPIN ────────────────────────────────────────────────────
echo "💡 Start Unpinging ..."
echo "   - Will download '${APK_NAME}' and patch into '${PATCHED_NAME}'"
docker run --rm \
  -v "${CERT_PATH}:/work/ca.pem:ro" \
  -v "${WORKDIR}:/work" \
  apk-mitm-unpin "\
    set -e; \
    curl -H 'User-Agent: ${CURL_USER_AGENT}' -SL '${APK_URL}' -o '${APK_NAME}' && \
    apk-mitm '${APK_NAME}' --certificate /work/ca.pem \
  "

# ─── SAVE PATCHED XAPK + EXTRACT ─────────────────────────────────────────────
mkdir -p data
cp "${WORKDIR}/${PATCHED_NAME}" "data/${PATCHED_NAME}"
if [[ "$APK_EXTENSION" == "xpak" ]]; then
  if ! unzip -o "data/${PATCHED_NAME}" -d data/apks; then
    echo "❌ Failed to unzip patched XAPK"
    exit 1
  fi
fi

# ─── OPTIONAL HOST-SIDE INSTALL ──────────────────────────────────────────────
echo "💡 Install patched APKs manually; patched APK version saved here: data/${PATCHED_NAME}"
echo '   - Manually install with:'
echo "     - apk : 'adb \"install data/${PATCHED_NAME}\"'"
echo "     - xapk: 'adb install-multiple data/apks/*.apk'"

echo "✅ All done! Patched (X)APK → data/${PATCHED_NAME}"
