# 📲 Using Bumper with the Official Android/iOS App

You can use the official "Ecovacs" or "Ecovacs Home" app to control your robot through your local Bumper server.
This requires:

- **DNS overrides** as described in [DNS Setup](../getting_started/dns.md).
- **Trusting Bumper's CA certificate** on your device
  (generated via [Certificates](../getting_started/certificates.md)).

!!! note

    Functionality may vary by app version, region, and robot model.
    Some features depend on cloud services and may not work with Bumper.

---

## 🔑 Install the Bumper CA Certificate

### iOS (iOS 10+)

1. Transfer `certs/ca.crt` (PEM format) to your device (for example, email or AirDrop).
2. Tap the file to open the install prompt.
3. In **Settings → Profile Downloaded**, tap **Install** and enter your passcode.
4. Go to **Settings → General → About → Certificate Trust Settings**.
5. Enable full trust for **Bumper CA**.

### Android

#### Android 6 and older (API 23 and below)

For older releases, install the CA as a user certificate:

1. Copy `certs/ca.crt` to device storage.
2. Go to **Settings → Security → Install from device storage**.
3. Select the certificate, name it, and choose **VPN and apps**.

#### Android 7 and newer (API 24 and above)

Apps that target API 24 or newer do not trust user-installed CAs by default.
There are two ways around that:

- Use the patched app. Its `android:debuggable="true"` flag activates the app's
  own `<debug-overrides>`, which makes it trust a user CA. Install `ca.crt` as a
  user certificate, then follow
  [Certificate Pinning Bypass (APP)](../internals/certificate-unpinning-app.md)
  for the app's MQTT pin.
- On Android 9 and lower, install the CA into the system store with `adb root`.
  This needs a debuggable or rooted build; production firmware rejects `adb root`:

    ```sh
    # Start adb as root
    adb root
    # Remount /system writable
    adb remount
    # Push CA into system store
    adb push certs/ca.crt "/system/etc/security/cacerts/$(openssl x509 -inform PEM -subject_hash_old -in certs/ca.crt | head -1).0"
    adb reboot
    ```

    Verify in **Settings → Security → Trusted credentials → System**.

    From Android 10 (API 29) the system partition is read-only, so a system-store
    install is not an option there; use the patched app instead.

!!! tip

    If your device or app still rejects the certificate,
    consider certificate-pinning bypass or a rooted-device approach.

!!! tip

    For emulators, see the **Prepare the Emulator** section in
    [Sniffing & Reverse Engineering](../internals/sniffing.md).

!!! note

    App-side pinning and native TLS stacks can still block specific paths even when SANs are correct.
    Check device logs when a single host fails.
    See [DNS Setup](../getting_started/dns.md#certificate-and-trust-notes).

---

## ⚙️ Configure the App

1. Launch **Ecovacs** / **Ecovacs Home**.
2. On the login screen, enter any email/password (6+ characters).
3. If your robot is connected to Bumper, it can appear in the device list.
4. Tap the robot; the app communicates with it through the services Bumper provides.

!!! note

    Bumper accepts logins for compatibility; real Ecovacs credentials are not validated by Bumper.

---

## ✨ Features

Voice language changes and work logs/maps are documented in [Features](features.md).
These features depend on required data/files and supported robot/app behavior.

---

## 🛠️ Troubleshooting

- **No robots found**: confirm DNS overrides, reachability/proxy routing, and that Bumper is reachable.
  The web UI is a status view; robots appear only after they connect to Bumper.
  See [Getting Started](../getting_started/index.md#what-to-expect).
- **Login errors**: ensure your CA is trusted and the HTTPS connection succeeds.
  Check app pinning/native TLS behavior when needed.
- **Missing features**: some cloud-only functions are not implemented.
  Supported local features (for example, voice files or work logs/maps) may still require data files or model support.
  See [Features](features.md).

---

## 📖 See Also

- [DNS Setup](../getting_started/dns.md)
- [Certificate Pinning Bypass (APP)](../internals/certificate-unpinning-app.md)
- [Architecture](../internals/architecture.md)
