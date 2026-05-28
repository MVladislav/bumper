# Defeating Certificate Pinning in the Ecovacs Home App

This guide covers methods to bypass certificate pinning in the Ecovacs Home Android application, enabling HTTPS interception for local Bumper usage.

> **⚠️ Disclaimer:**
>
> Modifying the Ecovacs app may break future updates. Proceed at your own risk.

---

## 📋 Prerequisites

- **Automated Script (NEW)**
    - > **NOTE:** Currently **working as well as possible** with newer app versions.  
      > However, **some app features may still fail** due to unresolved certificate pinning.
    - Docker (for building and running the patching container)
    - Android SDK platform-tools (`adb` in your PATH)
- **Automated Script (Old)**
    - > **NOTE:** Currently **not working well** with newer app versions `>3.4.0`
    - Docker (for building and running the patching container)
    - Android SDK platform-tools (`adb` in your PATH)
    - CA certificate at `./certs/ca.crt` (see [Create Certificates](../getting_started/certificates.md))
- **Manual apk-mitm Method**
    - > **NOTE:** Currently **not working well** with newer app versions `>3.4.0`
    - Node.js & npm
    - Java JDK
    - Android SDK platform-tools (`adb`)
    - `apk-mitm` (install via `npm install -g apk-mitm`)
- **Manual apktool Method**
    - > **NOTE:** Currently **not working well** with newer app versions `>3.4.0`
    - `apktool` (for decompile/recompile)
    - `keytool` and `apksigner` (part of Java JDK or Android build-tools)
    - Android SDK platform-tools (`adb`)
- **Manual android-unpinner Method**
    - > **NOTE:** Currently **not working well** with newer app versions `>3.4.0`
    - Python and `pip`
    - OpenJDK
    - Android SDK platform-tools (`adb`)
    - `android-unpinner` (for patch apk)

---

## ⭐ Recommended

### 🚀 Automated Script (NEW)

Bumper includes a Bash script at
[`scripts/create-unpinned-app.sh`](https://github.com/MVladislav/bumper/blob/main/scripts/create-unpinned-app.sh)
that automates the XAPK patching process inside Docker.

!!! note

    This script **only supports XAPK files** (not APKs) because `android-unpinner` patches each APK inside the XAPK individually.
    While most functionality works after patching, **some app features may still fail due to remaining certificate checks**.

#### How the Script Works

The script performs these steps internally:

1. **Environment Validation**  
   Checks for `docker`; exits if not found.

2. **Configuration**  
   Defines variables for:
    - Base Docker image (`python:3-slim`)
    - Ecovacs XAPK URL (configurable via `APK_URL`)
    - Temporary working directory

3. **Docker Image Build**  
   Constructs a minimal image named `apk-mitm-unpin` with:
    - OpenJDK 21 JRE
    - Python 3, `uv`, and `android-unpinner` (installed via `pip` and `uv`)
    - `git`, `curl`, `unzip`

4. **Download & Unpin**  
   Runs a container that:
    - Downloads the XAPK via `curl`
    - Extracts the XAPK and patches each APK using `android-unpinner`
    - Renames the patched APKs for clarity

5. **Extract & Save**  
   Copies the patched APKs to `data/<original-basename>/`.

6. **Manual Installation**  
   Prints instructions for manual installation via `adb install-multiple`.

#### Running the Script

```sh
scripts/create-unpinned-app.sh
```

> On completion, the patched APKs are saved under `data/<original-basename>/`.
> The script does **not** automatically install the APKs; it only provides the commands for manual installation.

### 🚀 Automated Script (OLD)

Bumper includes a Bash script at
[`scripts/create-unpinned-app-old.sh`](https://github.com/MVladislav/bumper/blob/main/scripts/create-unpinned-app-old.sh)
that automates the XAPK/APK patching process inside Docker.

#### How the Script Works

The script performs these steps internally:

1. **Environment Validation**
   Checks for `docker`; exits if not found.

2. **Configuration**
   Defines variables for:
    - Base Docker image (`node:25-slim`)
    - Ecovacs XAPK/APK URL (configurable via `APK_URL`)
    - Certificate path (`certs/ca.crt`)
    - Temporary working directory

3. **Docker Image Build**
   Constructs a minimal image named `apk-mitm-unpin` with:
    - OpenJDK 17 JRE
    - `apk-mitm` (installed via npm)
    - `curl`, `zip`, `unzip`

4. **Download & Unpin**
   Runs a container that:
    - Downloads the (X)APK via `curl`
    - Executes `apk-mitm` with the mounted CA certificate

5. **Extract & Save**
   Copies the patched (X)APK to `./data`; if the file is an XAPK, it is extracted to `data/apks`.

6. **Manual Installation**
   Prints instructions for manual installation via `adb install` (for APK) or `adb install-multiple` (for XAPK).

#### Running the Script

```sh
scripts/create-unpinned-app-old.sh
```

> On completion, the patched (X)APK is saved as `data/<original>-patched.<ext>`.
> The script does **not** automatically install the APK; it only provides the commands for manual installation.

---

## 🔧 Alternatives

> These methods are provided for reference and may work for specific app versions.
> They are not officially supported and may require adjustments.

### 🛠️ Manual apk-mitm Method

This method leverages `apk-mitm` to patch the XAPK directly.

**1. Download original XAPK:**

```sh
curl -SLo ./data/eco.xapk \
  'https://d.apkpure.net/b/XAPK/com.eco.global.app?version=latest'
```

**2. Patch with apk-mitm:**

```sh
apk-mitm './data/eco.xapk' --certificate './certs/ca.crt'
```

**3. Extract and install:**

```sh
unzip -o './data/eco-patched.xapk' -d ./data/apks
adb install-multiple ./data/apks/*.apk
```

### 🛠️ Manual apktool Method

Full manual unpack, patch, and re-sign process.

**1. Download and unpack:**

```sh
cd ./data
APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=127&nc=arm64-v8a'
APK_NAME="$(curl -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
curl -SLo "$APK_NAME" "$APK_URL"
unzip "$APK_NAME" -d bump && cd bump
```

**2. Prepare:**

```sh
curl -SLo apktool.jar https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.12.1.jar
export _JAVA_OPTIONS="-Djava.io.tmpdir=$HOME/.tmp"
```

**3. Decode with apktool:**

```sh
java -jar apktool.jar d 'com.eco.global.app.apk' --frame-path ~/.tmp/apktool-framework
```

**4. Insert network security config:**

??? note

    This step allows the app to trust user-installed certificates (e.g., your CA cert).

```sh
tee 'com.eco.global.app/res/xml/network_security_config.xml' > /dev/null <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system"/>
            <certificates src="user"/>
        </trust-anchors>
    </base-config>
</network-security-config>
EOF
```

**5. Rebuild the APK:**

```sh
sed -i 's/android:gravity="0x0"/android:gravity="center"/g' com.eco.global.app/res/layout/aa30_activity_air_auto.xml
java -jar apktool.jar b 'com.eco.global.app' --frame-path ~/.tmp/apktool-framework
cp 'com.eco.global.app/dist/com.eco.global.app.apk' 'com.eco.global.app.apk'
```

**6. Sign the APK(s):**

```sh
keytool -genkey -v -keystore bumper-key.jks -alias bumper-key \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass 123456 -keypass 123456 \
  -dname "CN=Bumper, OU=Bumper, O=Bumper, L=Home, S=Home, C=EU"

for apk in *.apk; do
  echo "Zipalign $apk"
  cp "$apk" "$apk.tmp"
  zipalign -p -f -v 4 "$apk.tmp" "$apk" 1>/dev/null
  rm -f "$apk.tmp"
done

for apk in *.apk; do
  echo "Signing $apk"
  apksigner sign \
    --ks bumper-key.jks \
    --ks-key-alias bumper-key \
    --ks-pass pass:123456 \
    --key-pass pass:123456 \
    --v1-signing-enabled true \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    "$apk"
done
```

**7. Install on device:**

```sh
adb install-multiple *.apk
```

### 🛠️ Manual android-unpinner Method

Full manual unpack, patch, and re-sign process.

**1. Download and unpack:**

```sh
cd ./data
APK_URL='https://d.apkpure.net/b/XAPK/com.eco.global.app?versionCode=127&nc=arm64-v8a'
APK_NAME="$(curl -sI -L "$APK_URL" | grep -o -E 'filename="[^"]+"' | cut -d'"' -f2)"
curl -SLo "$APK_NAME" "$APK_URL"
unzip "$APK_NAME" -d bump && cd bump
```

**2. Prepare:**

```sh
# sudo apt install openjdk-21-jre-headless
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install uv
uv tool install git+https://github.com/mitmproxy/android-unpinner
export _JAVA_OPTIONS="-Djava.io.tmpdir=$HOME/.tmp"
```

**3. Patch APKs:**

```sh
android-unpinner patch-apks *.apk
for file in *.unpinned.apk; do mv -f "$file" "${file%.unpinned.apk}.apk"; done
```

**4. Install on device:**

```sh
adb install-multiple *.apk
```

---

## 📚 References

- [apk-mitm (GitHub)](https://github.com/niklashigi/apk-mitm)
- [APKLab (GitHub)](https://github.com/APKLab/APKLab)
- [apktool](https://apktool.org)
- [objection (GitHub)](https://github.com/sensepost/objection)
- [Frida Certificate Pinning Bypass (HTTP Toolkit)](https://httptoolkit.com/blog/frida-certificate-pinning)

---

_For certificate creation and DNS setup, see [Create Certificates](../getting_started/certificates.md) and [DNS Setup](../getting_started/dns.md)._
