#!/usr/bin/env bash
set -Eeuo pipefail

# ─── PREREQS ─────────────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || {
  echo "❌ docker not found"
  exit 1
}
if ! command -v adb >/dev/null 2>&1; then
  echo "⚠️ adb not found in PATH; skipping host‑side install"
  SKIP_ADB_INSTALL=1
else
  SKIP_ADB_INSTALL=0
fi

# ─── TRAP ────────────────────────────────────────────────────────────────────
WORKDIR="$(mktemp -d)"
echo "$WORKDIR"
# WORKDIR="$PWD/tmp"
# mkdir -p "$WORKDIR "
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

IMAGE='node:18-slim'
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest' # >= 3.4.0
APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=117&nc=arm64-v8a&sv=21' # 3.3.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=109&nc=arm64-v8a&sv=21' # 3.0.0
# APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=107&nc=arm64-v8a&sv=21' # 2.5.9
# APK_URL='https://d.apkpure.net/b/APK/com.eco.global.app?versionCode=87&nc=arm64-v8a%2Carmeabi-v7a&sv=21' # 2.4.1
echo "💡 Collecting base information..."
APK_NAME="$(curl -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
APK_BASENAME="${APK_NAME%.*}"
APK_EXTENSION="${APK_NAME##*.}"
PATCHED_NAME="${APK_BASENAME}-patched.${APK_EXTENSION}"
CERT_PATH="$(pwd)/certs/ca.crt"
[ -f "$CERT_PATH" ] || {
  echo "❌ Certificate not found at $CERT_PATH"
  exit 1
}

# ─── BUILD TEMP IMAGE ────────────────────────────────────────────────────────
echo "💡 Docker image will be build..."
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
echo "💡 Unpinging starting..."
echo "   - Will download '${APK_NAME}' and patch into '${PATCHED_NAME}'"
docker run --rm \
  -v "${CERT_PATH}:/work/ca.pem:ro" \
  -v "${WORKDIR}:/work" \
  apk-mitm-unpin "\
    set -e; \
    curl -SL '${APK_URL}' -o '${APK_NAME}' && \
    apk-mitm '${APK_NAME}' --certificate /work/ca.pem \
  "

# ─── SAVE PATCHED XAPK + EXTRACT ─────────────────────────────────────────────
mkdir -p data
cp "${WORKDIR}/${PATCHED_NAME}" "data/${PATCHED_NAME}"
unzip -o "data/${PATCHED_NAME}" -d data/apks

# ─── OPTIONAL HOST‑SIDE INSTALL ──────────────────────────────────────────────
if ((SKIP_ADB_INSTALL == 0)); then
  echo "🔌 Installing patched APKs via adb…"
  adb install-multiple data/apks/*.apk
else
  echo "💡 Skipping adb install; patched APK is here: data/${PATCHED_NAME}"
  echo '   - You can run manually: "adb install-multiple data/apks/*.apk"'
fi

echo "✅ All done! Patched (X)APK → data/${PATCHED_NAME}"
