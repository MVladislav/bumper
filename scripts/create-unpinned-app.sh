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
IMAGE='python:3-slim'
APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest' # >= 3.12.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=129&nc=armeabi-v7a' # 3.11.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=128&nc=armeabi-v7a' # 3.10.0
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
# APK_URL='https://d.apkpure.net/b/APK/com.eco.global.app?versionCode=87&nc=arm64-v8a' # 2.4.1
echo "💡 Collecting base information..."
APK_NAME="$(curl -H "User-Agent: ${CURL_USER_AGENT}" -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
APK_BASENAME="${APK_NAME%.*}"
APK_EXTENSION="${APK_NAME##*.}"
[[ "$APK_EXTENSION" == "apk" ]] && { echo "❌ '.apk' files are not supported with this script, only '.xapk' will work!"; exit 1; }

# ─── BUILD TEMP IMAGE ────────────────────────────────────────────────────────
echo "💡 Building Docker image..."
docker build --pull --rm -q -t apk-mitm-unpin - <<EOF
FROM ${IMAGE}
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      git curl unzip openjdk-21-jre-headless \
 && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install uv
RUN uv tool install git+https://github.com/mitmproxy/android-unpinner
WORKDIR /work
ENTRYPOINT ["sh","-c"]
EOF

# ─── RUN DOWNLOAD + UNPIN ────────────────────────────────────────────────────
echo "💡 Start Unpinging ..."
echo "   - Will download '${APK_NAME}' and patch apk's into '${WORKDIR}/*.apk'"
docker run --rm \
  -v "${WORKDIR}:/work" \
  apk-mitm-unpin "\
    set -e; \
    curl -H 'User-Agent: ${CURL_USER_AGENT}' -SL '${APK_URL}' -o '${APK_NAME}' && \
    unzip '${APK_NAME}' && rm -f '${APK_NAME}' && \
    ~/.local/bin/android-unpinner patch-apks *.apk && \
    for file in *.unpinned.apk; do mv -f \"\$file\" \"\${file%.unpinned.apk}.apk\"; done && \
    chmod -R o+rw '/work/' >/dev/null | true
  "

# ─── SAVE PATCHED XAPK + EXTRACT ─────────────────────────────────────────────
PATCHED_VERSION_PATH="data/$APK_BASENAME"
mkdir -p "${PATCHED_VERSION_PATH}/"
cp -r "${WORKDIR}/"*.apk "${PATCHED_VERSION_PATH}/"

# ─── OPTIONAL HOST-SIDE INSTALL ──────────────────────────────────────────────
echo "💡 Install patched APKs manually; patched (X)APK version saved under: '${PATCHED_VERSION_PATH}/'"
echo '   - Manually install with:'
echo "     - xapk: 'adb install-multiple ${PATCHED_VERSION_PATH}/*.apk'"

echo "✅ All done! Patched (X)APK → '${PATCHED_VERSION_PATH}/'"
