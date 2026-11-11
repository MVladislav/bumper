# Android Sniffing on Ubuntu with mitmproxy

This guide walks you through setting up an Android emulator on Ubuntu,
installing a custom CA certificate, and using mitmproxy to intercept traffic.
It also includes an optional Python addon for enhanced output filtering.

---

## 📋 Prerequisites

- **Ubuntu 22.04+**
- **Docker** (for running mitmproxy)
- **Android Studio** (for emulator and ADB)
- **CA certificate** (`ca.crt` and `ca.pem`) in the `./certs/` folder
    - Created by `bash scripts/certs/create-cert.sh` or by Bumper at startup;
      see [Certificates](../getting_started/certificates.md)

---

## 🚀 Install Android Studio & SDK

Install Android Studio via Snap:

```sh
sudo snap install android-studio --classic
```

Launch Android Studio and follow the initial setup to install the SDK and platform-tools.

!!! tip

    Install the SDK under `~/.android/Sdk` for consistency.

---

## 🖥️ Create an Emulator

1. Open **AVD Manager** (Virtual Device Manager).
2. Click **Create Virtual Device**.
3. Choose a device (e.g., Pixel 6 Pro) **without** Google Play Store.
4. Select a system image with **API 28 (Android 9 Pie)** or lower to allow system CA installation.

---

## 🔧 Prepare the Emulator

_(Optional)_ Disable Quickboot file-backed feature (can help with BTRFS-related emulator issues):

```sh
echo "QuickbootFileBacked = off" >> ~/.android/advancedFeatures.ini
```

List available AVDs:

```sh
~/.android/Sdk/emulator/emulator -list-avds
```

Start the emulator with root access and writable system.
Replace `<AVD_NAME>` with an AVD from the list above:

```sh
~/.android/Sdk/emulator/emulator \
    -avd <AVD_NAME> \
    -writable-system \
    -no-boot-anim \
    -gpu host \
    -cores 4 \
    -memory 4096
```

Restart ADB as root and remount:

```sh
~/.android/Sdk/platform-tools/adb root
~/.android/Sdk/platform-tools/adb remount
```

---

## 🔒 Install the CA Certificate

Push your custom CA into the emulator's system trust store. The emulator must
be started with `-writable-system` and ADB remounted as root (see
[Prepare the Emulator](#prepare-the-emulator)):

```sh
HASH=$(openssl x509 -inform PEM -subject_hash_old -in certs/ca.crt | head -1)
~/.android/Sdk/platform-tools/adb push certs/ca.crt "/system/etc/security/cacerts/${HASH}.0"
~/.android/Sdk/platform-tools/adb reboot
~/.android/Sdk/platform-tools/adb wait-for-device
```

!!! note

    On Android 10 and newer the system partition is read-only. Install the CA
    as a user certificate instead, and use an app that trusts user CAs (for
    example the patched app from
    [Defeating Certificate Pinning](certificate-unpinning-app.md)).

---

## 📱 Install the Target App and Proxy App

### 1️⃣ Install Ecovacs Home App

Download and install version `2.4.1` of the Ecovacs Home APK:

!!! note

    To reverse newer app versions, you need to unpin the certificate first.
    See [Defeating Certificate Pinning](certificate-unpinning-app.md) for instructions.

    - [Ecovacs Home on APKPure](https://apkpure.net/ecovacs-home/com.eco.global.app) (older versions may be easier to inspect; newer versions may require [certificate pinning bypass](certificate-unpinning-app.md))

Install the app on the emulator:

```sh
~/.android/Sdk/platform-tools/adb install <path/to/Ecovacs_Home_2.4.1.apk>
```

!!! tip

    Drag-and-drop the APK onto the emulator window.

### 2️⃣ Install SOCKS5 Proxy App

Install a SOCKS5 proxy client (e.g., Super Proxy):

- Use a SOCKS5 proxy app on the emulator/device (for example, [Proxy Server on APKPure](https://apkpure.net/proxy-server/com.icecoldapps.proxyserver) or another SOCKS5 client; verify the app/package before installing).

---

## 🌐 Configure Proxy on Android

In the emulator's network or proxy app settings:

- **Protocol**: SOCKS5
- **Host**: `<YOUR_SERVER_IP>`
- **Port**: `1080`

This routes all emulator traffic through mitmproxy.

---

## ⚙️ Run mitmproxy with Docker Compose / Swarm

The repository includes `docker-compose-mitm.yaml` with pre-defined mitmproxy settings and helper scripts.
It uses `certs/ca.pem`, so make sure your Bumper certificates exist.

**Docker Compose**

```sh
docker compose -f docker-compose-mitm.yaml up -d
```

**Docker Swarm**

!!! note "Alias"

    This uses the [`docker-swarm-compose` alias](https://github.com/MVladislav/.dotfiles/blob/main/profiles/profile5-containers#L9).
    Pass the compose file with `-f`; setting `COMPOSE_FILE` is not enough. The
    final argument is the stack name.

```sh
docker-swarm-compose -f docker-compose-mitm.yaml mitm
```

Access [http://localhost:8081](http://localhost:8081) to inspect traffic.

---

## 🐍 Optional: Python Script Addons

`docker-compose-mitm.yaml` mounts helper scripts from `configs/` (`mitm-cmd.py`, `mitm-mqtt.py`, `mitm-dns.py`).
Script loading is controlled by environment variables, so you can enable only what you need:

| Variable           | Default | Script              | Purpose                             |
| ------------------ | ------- | ------------------- | ----------------------------------- |
| `MITM_SCRIPT_CMD`  | `1`     | `/tmp/mitm-cmd.py`  | Capture/filter HTTP command traffic |
| `MITM_SCRIPT_MQTT` | `0`     | `/tmp/mitm-mqtt.py` | MQTT sniffing                       |
| `MITM_SCRIPT_DNS`  | `1`     | `/tmp/mitm-dns.py`  | DNS helper/filtering                |

Examples:

```sh
# Enable MQTT sniffing in addition to defaults
MITM_SCRIPT_MQTT=1 docker compose -f docker-compose-mitm.yaml up -d

# Only the MQTT script
MITM_SCRIPT_CMD=0 MITM_SCRIPT_MQTT=1 MITM_SCRIPT_DNS=0 docker compose -f docker-compose-mitm.yaml up -d
```

You can also set `MITM_WEB_PW` to change the mitmweb password (default: `mitm`) and `MITM_PATH` for capture output.

---

## 🛠️ Troubleshooting

- **SSL errors**: Verify the CA hash and placement.
- **Emulator won't root**: Use API 28 or lower with `-writable-system`.
- **App 2003 errors**: Launch the app once without proxy to fetch initial data.

---

## 📚 Resources

- [mitmproxy MQTT script example](https://github.com/nikitastupin/mitmproxy-mqtt-script)
- [Custom CA usage](https://docs.mitmproxy.org/stable/concepts-certificates/#using-a-custom-certificate-authority)
- [mitmproxy documentation](https://docs.mitmproxy.org/stable/)
