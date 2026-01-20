# Android Sniffing on Ubuntu with mitmproxy

This guide walks you through setting up an Android emulator on Ubuntu, installing a custom CA certificate, and using mitmproxy to intercept traffic. It also includes an optional Python addon for enhanced output filtering.

---

## 📋 Prerequisites

- **Ubuntu 22.04+**
- **Docker** (for running mitmproxy)
- **Android Studio** (for emulator and ADB)
- **CA certificate** (`ca.crt` and `ca.pem`) placed in the `./certs/` folder
    - These are generated automatically when Bumper starts for the first time

---

## 🚀 Install Android Studio & SDK

Install Android Studio via Snap:

```sh
$sudo snap install android-studio --classic
```

Launch Android Studio and follow the initial setup to install the SDK and platform-tools.

> _Tip:_ Install the SDK under `~/.android/Sdk` for consistency.

---

## 🖥️ Create an Emulator

1. Open **AVD Manager** (Virtual Device Manager).
2. Click **Create Virtual Device**.
3. Choose a device (e.g., Pixel 6 Pro) **without** Google Play Store.
4. Select a system image with **API 28 (Android 9 Pie)** or lower to allow system CA installation.

---

## 🔧 Prepare the Emulator

_(Optional)_ Disable Quickboot file-backed feature
[Reddit Source - fixes BTRFS issues](https://www.reddit.com/r/btrfs/comments/l8qu3l/comment/gowtd55/?utm_source=share&utm_medium=web2x&context=3):

```sh
$echo "QuickbootFileBacked = off" >> ~/.android/advancedFeatures.ini
```

List available AVDs:

```sh
$~/.android/Sdk/emulator/emulator -list-avds
```

Start the emulator with root access and writable system:

> _replace `<AVD_NAME>`_

```sh
$~/.android/Sdk/emulator/emulator \
    -avd <AVD_NAME> \
    -writable-system \
    -no-boot-anim \
    -gpu host \
    -cores 4 \
    -memory 4096
```

Restart ADB as root and remount:

```sh
$~/.android/Sdk/platform-tools/adb root
$~/.android/Sdk/platform-tools/adb remount
```

---

## 🔒 Install the CA Certificate

Push your custom CA into the emulator’s system trust store:

```sh
$HASH=$(openssl x509 -inform PEM -subject_hash_old -in certs/ca.crt | head -1)
$~/.android/Sdk/platform-tools/adb push certs/ca.crt "/system/etc/security/cacerts/${HASH}.0"
$~/.android/Sdk/platform-tools/adb reboot
$~/.android/Sdk/platform-tools/adb wait-for-device
```

---

## 📱 Install the Target App and Proxy App

### 1️⃣ Install Ecovacs Home App

Download and install version `2.4.1` of the Ecovacs Home APK:

> If you want to try reversing newer app versions,
> you'll need to unpin the certificate.
> See **[Defeating Certificate Pinning](../internals/certificate-unpinning-app.md)** for instructions.

- [Ecovacs Home on APKPure](https://apkpure.net/ecovacs-home/com.eco.global.app/download/2.4.1)
- [Ecovacs Home on Aptoide](https://ecovacs-home.en.aptoide.com/app)

```sh
$~/.android/Sdk/platform-tools/adb install <path/to/Ecovacs_Home_2.4.1.apk>
```

> _Tip:_ Drag-and-drop the APK onto the emulator window.

### 2️⃣ Install SOCKS5 Proxy App

Install a SOCKS5 proxy client (e.g., Super Proxy):

- [Super Proxy on APKPure](https://apkpure.net/super-proxy/com.scheler.superproxy)
- [Super Proxy on Aptoide](https://super-proxy-scheler-software.en.aptoide.com/app)

---

## 🌐 Configure Proxy on Android

In the emulator’s network or proxy app settings:

- **Protocol**: SOCKS5
- **Host**: `<YOUR_SERVER_IP>`
- **Port**: `1080`

This routes all emulator traffic through mitmproxy.

---

## ⚙️ Run mitmproxy in Docker-Swarm

From your project root:

> NOTE: i run my projects in `swarm mode`,
> mitm will be started with pre-defined configs inside `docker-compose-mitm.yaml`

```sh
$docker compose -f docker-compose-mitm.yaml --compatibility config | \
  sed 's|cpus: \([0-9]\+\(\.[0-9]\+\)*\)|cpus: "\1"|' | \
  sed '1{/^name:/d}' | \
  sed 's/published: "\(.*\)"/published: \1/' | \
  sed 's|mode: "\([0-9]\+\)"|mode: \1|' | \
  docker stack deploy --resolve-image=never --with-registry-auth --detach=false --compose-file - mitm
```

Access [http://localhost:8081](http://localhost:8081) to inspect traffic.

---

## 🐳 Alternative: Local mitmproxy Docker Run

From your project root (where `./certs/ca.pem` lives):

```sh
$docker run --rm -it --network host \
  -v $PWD/mitm:/home/mitm:ro \
  -v $PWD/certs/ca.pem:/tmp/ca.pem:ro \
  mitmproxy/mitmproxy mitmweb \
    --web-host 0.0.0.0 \
    --mode socks5 \
    --showhost \
    --rawtcp \
    --ssl-insecure \
    --certs '*=/tmp/ca.pem' \
    --set connection_strategy=lazy
```

Access [http://localhost:8081](http://localhost:8081) to inspect traffic.

---

## 🐍 Optional: Python Script Filter

Use the Python addon at `./configs/mitm.py` to filter or transform flows:

```sh
$docker run --rm -it --network host \
  -v $PWD/mitm:/home/mitm:ro \
  -v $PWD/certs/ca.pem:/tmp/ca.pem:ro \
  -v $PWD/configs/mitm.py:/tmp/mitm.py:ro \
  mitmproxy/mitmproxy mitmweb \
    --web-host 0.0.0.0 \
    --mode socks5 \
    --showhost \
    --rawtcp \
    --ssl-insecure \
    --certs '*=/tmp/ca.pem' \
    --set connection_strategy=lazy \
    -s /tmp/mitm.py
```

Access [http://localhost:8081](http://localhost:8081) to inspect traffic.

---

## 🛠️ Troubleshooting

- **SSL errors**: Verify the CA hash and placement.
- **Emulator won’t root**: Use API 28 or lower with `-writable-system`.
- **App 2003 errors**: Launch the app once without proxy to fetch initial data.

---

## 📚 Resources

- [mitmproxy MQTT script example](https://github.com/nikitastupin/mitmproxy-mqtt-script)
- [Custom CA usage](https://docs.mitmproxy.org/stable/concepts-certificates/#using-a-custom-certificate-authority)
- [mitmproxy API docs](https://docs.mitmproxy.org/stable/api/)
