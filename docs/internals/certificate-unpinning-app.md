# Defeating Certificate Pinning in the Ecovacs Home App

This guide covers how to make the Ecovacs Home Android app trust your own
Bumper instance, so the app talks only to your LAN.

> **⚠️ Disclaimer:**
>
> Modifying the Ecovacs app may break future updates. Proceed at your own risk.

---

## 📋 Methods

Five ways to do this are documented below. Each needs different tools, so check
its own **Needs:** line. Only the first is maintained.

| Method                                                      | Needs                | MQTT works | Maintained |
| ----------------------------------------------------------- | -------------------- | ---------- | ---------- |
| [Automated script](#-automated-script-latest)               | docker               | yes        | yes        |
| [Automated script (legacy)](#-automated-script-legacy)      | docker               | -          | no         |
| [Manual apk-mitm](#-manual-apk-mitm-method)                 | node, npm, java, adb | -          | no         |
| [Manual apktool](#-manual-apktool-method)                   | java, adb            | -          | no         |
| [Manual android-unpinner](#-manual-android-unpinner-method) | python, java, adb    | -          | no         |

The three manual methods are reference material: they work in principle but are
untested against current app versions. None of them applies the MQTT patch, so
with those the web API works and robot control depends on app version.

---

## ⭐ Recommended

### 🚀 Automated script (latest)

**Needs:** `docker`, and nothing else. The download, the patching and the
signing all run inside a container, so your host stays clean. You also need
`adb` and `certs/ca.crt` (see
[Create Certificates](../getting_started/certificates.md)) for the device steps
below, plus an **arm64 device** - see [Device requirement](#-device-requirement).

#### What it does

1. Downloads the app (XAPK or APK) and unpacks its splits.
2. Sets `android:debuggable="true"` in the manifest, which activates the app's
   own `<debug-overrides><certificates src="user"/>`. That is what makes the
   platform trust your user-installed CA.
3. Makes the certificate Ecovacs hardcodes for MQTT unusable, so that channel
   also falls back to the platform trust store.
4. Runs `zipalign` and re-signs every split with a key kept in `certs/`.
5. Verifies the result and prints the `adb` command to install it.

Steps 2 and 3 are both required. Without step 3 no robot command arrives, because
every command is relayed over MQTT.

[`scripts/create-unpinned-app.sh`](https://github.com/MVladislav/bumper/blob/main/scripts/create-unpinned-app.sh)
writes the installable APKs to `data/<app-name>/`.

```sh
scripts/create-unpinned-app.sh
```

All of it runs in a container (`bumper-apk-tool`: JDK, Android build-tools,
python3, curl). The only things written outside the container are
`data/<app-name>/` and the signing key `certs/bumper-apk.jks`; the download, the
unpacked splits and the intermediate copies all disappear with the container.
Editing a patcher only rebuilds the image's last layer.

**1.** Install the APKs. The script prints the exact command:

```sh
adb install-multiple --no-incremental data/<app-name>/*.apk
```

**2.** Install Bumper's CA on the phone as a **user CA certificate**:
Settings → Security → Encryption & credentials → Install a certificate → CA
certificate, and select `certs/ca.crt`. The script does not do this for you.

**3.** Point the app at your Bumper instance (see [DNS Setup](../getting_started/dns.md)).

#### Device requirement

**An arm64 Android device, or an arm64 emulator.** The account screens are React
Native, so they need `libhermes.so`. `base.apk` contains no native code at all -
every `.so` lives in the per-ABI split - and `SoLoader` searches only
`lib/<SUPPORTED_ABIS[0]>` inside the APKs, one ABI, not a loop.

An x86_64 emulator reports `SUPPORTED_ABIS: x86_64, arm64-v8a`, and the app
publishes no x86_64 build at any version, so `libhermes.so` is never found and
the main activity dies in `onCreate` with `SoLoaderDSONotFoundError`. That is the
white screen. Downgrading the app does not help: React Native and Hermes are
already present in 3.11.0.

On an x86_64 host, an `arm64-v8a` system image can be booted under the
emulator's bundled QEMU, which makes `SUPPORTED_ABIS[0]` `arm64-v8a` and the app
install the arm64 split. Expect a slow boot (tens of minutes) - it is not an
officially supported host architecture for that image.

#### The two patches

**1. `android:debuggable="true"`** - the app ships a `network_security_config.xml`
containing

```xml
<debug-overrides>
    <trust-anchors><certificates src="user"/></trust-anchors>
</debug-overrides>
```

Android applies `<debug-overrides>` to every domain, but only to a debuggable
app. Setting that one flag is what makes the platform trust your user-installed
CA, covering the web API, CodePush and the H5 pages. Nothing on those paths pins
a certificate.

**2. Neutralising the MQTT certificate pin** - MQTT is the exception, and it is
a real pin. The app's Paho fork builds its `SSLSocketFactory` from a certificate
embedded in a `classes*.dex`, loads it into an empty `KeyStore`, and passes that
to `TrustManagerFactory.init()`. A non-null, app-supplied KeyStore replaces the
platform trust store entirely, so `<debug-overrides>` and every user CA are
ignored and the handshake fails with `CertPathValidatorException: Trust anchor
for certification path not found`.

The patch keeps a prefix of that embedded string - enough for the dex's
`string_ids` table to stay sorted, which ART verifies on every launch - and fills
the rest with a marker. `CertificateFactory` then rejects the result, the app's
factory catches the exception and returns `null`, and Paho builds its
`SSLContext` with **null trust managers**: the platform trust store again. The
result contains no reference to Bumper's CA, so it stays valid when Bumper
regenerates its certificates.

#### Notes

- **Re-signing changes the app's signature.** The first install replaces any
  existing copy and clears its data, so you will have to log in again. Keep
  `certs/bumper-apk.jks` - the script reuses it on later runs so upgrades keep
  your session.
- Set `APK_URL` near the top of the script to patch a different app version.

#### Troubleshooting

**"Trust anchor for certification path not found" in logcat, robot never
reacts.** The MQTT pin is still in place - the app was built with
`SKIP_MQTT_CA=1`, or with an older version of the script. Rebuild and reinstall.

**The app installs but the login screen is white.** The main activity crashed.
Check logcat for `SoLoaderDSONotFoundError`; that means the device ABI does not
match the split, so use an arm64 device. The script prints the ABIs it produced
at the end of the build.

```sh
docker run --rm --entrypoint python3 -v "$PWD/scripts/apk-patch:/p:ro" \
  bumper-apk-tool /p/test_patch_mqtt_trust.py
```

---

## 🔧 Alternatives

!!! warning

    These predate the script above, do not apply the MQTT patch, and are not
    tested against current app versions. Prefer the script above.

### 🚀 Automated script (legacy)

**Needs:** `docker` only, like the script above.

[`scripts/create-unpinned-app-legacy.sh`](https://github.com/MVladislav/bumper/blob/main/scripts/create-unpinned-app-legacy.sh)
runs `apk-mitm` in a container, which rewrites the APK so it trusts the CA you
pass to it. Two differences from the latest script:

- It **embeds Bumper's CA** into the app instead of relying on a user-installed
  one, so no certificate has to be installed on the phone - but it has to be
  rebuilt whenever Bumper regenerates its certificates.
- It does not touch MQTT, so robot control will not work.

Kept because it patches differently, and is worth having when the latest
script's manifest edit stops working on a future app version.

```sh
scripts/create-unpinned-app-legacy.sh
```

### 🛠️ Manual apk-mitm Method

**Needs:** `node`, `npm`, a JDK, `adb`, and `certs/ca.crt`.

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

**Needs:** a JDK (for `keytool`, `apksigner`, `java`), `apktool`, `curl`, `unzip`, `adb`.

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

**Needs:** `python3`, `pip`/`uv`, a JDK, `curl`, `unzip`, `adb`.

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
