# Defeating Certificate Pinning in the Ecovacs Home App

This guide covers methods to bypass certificate pinning in the Ecovacs Home Android application, enabling HTTPS interception for local Bumper usage.

> **Disclaimer:** Modifying the Ecovacs app may break future updates. Proceed at your own risk.

---

## 📋 Prerequisites

-   **Automated Script**
    -   Docker (for building and running the patching container)
    -   Android SDK platform-tools (`adb` in your PATH)
    -   CA certificate at `./certs/ca.crt` (see [Create Certificates](../getting_started/certificates.md))
-   **Manual apk-mitm Method**
    -   Node.js & npm
    -   Java JDK
    -   Android SDK platform-tools (`adb`)
    -   `apk-mitm` (install via `npm install -g apk-mitm`)
-   **Manual apktool Method**
    -   `apktool` (for decompile/recompile)
    -   `keytool` and `apksigner` (part of Java JDK or Android build-tools)
    -   Android SDK platform-tools (`adb`)

---

## 🚀 Automated Script

Bumper includes a Bash script at
[`scripts/create-unpinned-app.sh`](https://github.com/MVladislav/bumper/blob/main/scripts/create-unpined-app.sh)
that automates the XAPK patching process inside Docker.

### How the Script Works

The script performs these steps internally:

1. **Environment Validation**  
   Checks for `docker`; warns if `adb` is missing (skipping host‑side install).

2. **Configuration**  
   Defines variables for the base Docker image (`node:18-slim`), the Ecovacs XAPK URL(s), certificate path, and a temporary working directory.

3. **Docker Image Build**  
   Constructs a minimal image named `apk-mitm-unpin` with:

    - OpenJDK 17 JRE
    - `apktool`, `apk-mitm`, `zip`, `unzip`, `curl`

4. **Download & Unpin**  
   Runs a container mount:

    - Downloads the XAPK via `curl` using the defined URL
    - Executes `apk-mitm` with the mounted CA certificate

5. **Extract & Save**  
   Copies the patched XAPK to `./data`, extracts APK files under `data/apks`.

6. **Optional ADB Install**  
   If `adb` is available, installs all APK parts via `adb install-multiple`.

### Running the Script

```sh
$scripts/create-unpinned-app.sh
```

> On completion, the patched XAPK is saved as `data/<original>-patched.xapk`.
> If `adb` was available, the APK is installed on a connected device.

---

## 🔧 Manual apk-mitm Method

This method leverages `apk-mitm` to patch the XAPK directly.

**Download original XAPK:**

```sh
$curl -SLo ./data/eco.xapk \
  'https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest'
```

**Patch with apk-mitm:**

```sh
$apk-mitm './data/eco.xapk' --certificate './certs/ca.crt'
```

**Extract and install:**

```sh
$unzip -o './data/eco-patched.xapk' -d ./data/apks
$~/.android/Sdk/platform-tools/adb install-multiple ./data/apks/*.apk
```

---

## 🛠️ Manual apktool Method

Full manual unpack, patch, and re-sign process.

**1. Download and unpack:**

```sh
$cd ./data
$APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest'
$APK_NAME="$(curl -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
$curl -SL "$APK_URL" -o "$APK_NAME"
$unzip "$APK_NAME" -d bump && cd bump
```

**2. Decode with apktool:**

```sh
$apktool d 'com.eco.global.app.apk' --frame-path /tmp/apktool-framework
```

**3. Insert network security config:**

```sh
$tee 'com.eco.global.app/res/xml/network_security_config.xml' > /dev/null <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <debug-overrides>
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
EOF
```

**4. Rebuild the APK:**

```sh
$apktool b 'com.eco.global.app' --frame-path /tmp/apktool-framework
$cp 'com.eco.global.app/dist/com.eco.global.app.apk' 'com.eco.global.app.apk'
```

**5. Sign the APK(s):**

```sh
$keytool -genkey -v -keystore bumper-key.jks -alias bumper-key \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass 123456 -keypass 123456 \
    -dname "CN=Bumper, OU=Bumper, O=Bumper, L=Home, S=Home, C=EU"

# NOTE: You need also (re)sign all other apk's
$~/.android/Sdk/build-tools/36.0.0/apksigner sign \
    --ks bumper-key.jks \
    --ks-key-alias bumper-key \
    --ks-pass pass:123456 \
    --key-pass pass:123456 \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    'com.eco.global.app.apk'
```

**6. Install on device:**

```sh
$~/.android/Sdk/platform-tools/adb install-multiple *.apk
```

---

## 📚 References

-   <https://github.com/niklashigi/apk-mitm>
-   <https://github.com/APKLab/APKLab>
-   <https://apktool.org>
-   <https://github.com/sensepost/objection>
-   <https://httptoolkit.com/blog/frida-certificate-pinning/>

---

_For certificate creation and DNS setup, see [Create Certificates](../getting_started/certificates.md) and [DNS Setup](../getting_started/dns.md)._
