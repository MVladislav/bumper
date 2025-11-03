# Using Bumper with the Official Android/iOS App

You can use the official “Ecovacs” or “Ecovacs Home” app to control your robot via your local Bumper server. This requires:

- **DNS overrides** as described in [DNS Configuration](../getting_started/dns.md).
- **Trusting Bumper’s CA certificate** on your device (generated via [Create Certificates](../getting_started/certificates.md)).

> **Note:** Functionality may vary by app version; some features (e.g., push notifications) depend on cloud services and may not work.

---

## 🔑 Install the Bumper CA Certificate

### iOS (iOS 10+)

1. Transfer `certs/ca.crt` (DER format) to your device (e.g., email or AirDrop).
2. Tap the file to open the install prompt.
3. In **Settings → Profile Downloaded**, tap **Install** and enter your passcode.
4. Go to **Settings → General → About → Certificate Trust Settings**.
5. Enable full trust for **Bumper CA**.

### Android

#### Android < 7 (API 23–27)

For older releases, install the CA as a user certificate:

1. Copy `certs/ca.crt` to device storage.
2. Go to **Settings → Security → Install from device storage**.
3. Select the cert, name it, and choose **VPN and apps**.

> _Tip:_ If your device or app still rejects the cert, consider pin-bypass or using a rooted device.

#### Android ≤ 9 (API 28 and below)

On Android Pie (9) and lower, you can install the CA as a system certificate via `adb`:

```sh
# Start adb as root
$adb root
# Remount /system writable
$adb remount
# Push CA into system store
$adb push certs/ca.crt "/system/etc/security/cacerts/$(openssl x509 -inform PEM -subject_hash_old -in certs/ca.crt | head -1).0"
$adb reboot
```

Verify in **Settings → Security → Trusted credentials → System**.

> **Tip:** For emulators, see the **Prepare the Emulator** section in [Android Sniffing](../internals/sniffing.md).

#### Android ≥ 10 (API 29 and above)

Starting with Android 10, user or system CA installation does not work for apps targeting API 29+. You must bypass certificate pinning instead:

- Follow the steps in [Certificate Pinning Bypass](../internals/certificate-unpinning-app.md).

---

## 📲 Configure the App

1. Launch **Ecovacs Home**.
2. On the login screen, enter any email/password (6+ characters).
3. If your robot is bound to Bumper, it appears in the device list.
4. Tap the robot; the app pings it over MQTT or XMPP and opens the control interface.

> **Note:** No real credential validation occurs; Bumper accepts all logins for compatibility.

---

## 🛠️ Troubleshooting

- **No robots found**: Confirm DNS overrides and that Bumper is reachable at `https://<domain>`.
- **Login errors**: Ensure your CA is trusted and HTTPS connection succeeds.
- **Missing features**: Some cloud-only functions (e.g., map history) are not implemented.

---

## 📖 See Also

- [DNS Configuration](../getting_started/dns.md)
- [Certificate Pinning Bypass](../internals/certificate-unpinning-app.md)
- [How Bumper Works](../internals/architecture.md)
