# 🌐 DNS Configuration for Bumper

To intercept and redirect traffic from Ecovacs robots and the official app to your local **Bumper** server,
configure your network's DNS resolver to override specific Ecovacs domains to your server's IP.

---

## 🔧 Recommended: OPNsense + Unbound DNS

If you're using OPNsense as your router/firewall, Unbound DNS is the default resolver.
Override domain resolution by adding host overrides:

1. **Login** to the OPNsense web interface.
2. Navigate to **Services → Unbound DNS → Overrides**.
3. Under **Host Overrides**, click **Add** and set:
    - **Host**: `*`
    - **Domain**: `ecouser.net`
    - **IP**: `<BUMPER_SERVER_IP>` (e.g. `192.168.1.100`)
4. Repeat for each of the other domains (host `*`, domain as below):
    - `ecouser.com`
    - `ecovacs.com`
    - `ecovacs.net`
5. Click **Apply** to reload Unbound.

!!! note

    These wildcard entries catch all subdomains under the specified domain.

---

## 📦 Alternative: dnsmasq / Pi-hole

If you're using DNSMasq directly or via Pi-hole, create a custom config file:

```txt
/etc/dnsmasq.d/02-bumper.conf
```

```txt
address=/ecouser.com/<BUMPER_SERVER_IP>
address=/ecouser.net/<BUMPER_SERVER_IP>
address=/ecovacs.com/<BUMPER_SERVER_IP>
address=/ecovacs.net/<BUMPER_SERVER_IP>
```

Replace `<BUMPER_SERVER_IP>` with your server's local IP (e.g. `192.168.1.100`).

**Apply changes:**

- **dnsmasq**: `sudo systemctl reload dnsmasq`
- **Pi-hole**: `pihole restartdns` or via the web UI

### ⚠️ Pi-hole v6 and `dnsmasq.d`

Pi-hole v6 does **not** ingest custom configs in `/etc/dnsmasq.d/` by default;
this behavior is disabled in FTL.
See [Pi-hole discourse](https://discourse.pi-hole.net/t/etc-dnsmasq-d-is-disabled-after-upgrading-to-v6/76059).
You must explicitly re-enable it:

- **ENV**: add `FTLCONF_misc.dnsmasq_d=true`
- **GUI**: in the Pi-hole web UI, go to **Settings > All settings page - Miscellaneous** and enable the option.

Without this, custom `02-bumper.conf`-style entries are silently ignored.

---

## 📋 Notes on Domain Patterns

If overriding DNS for top-level domains (like `*.ecovacs.com`) is not supported in your DNS setup,
you must manually configure each relevant subdomain used by the app or robot.

EcoVacs robots and the companion app connect to different domains depending on country/region,
app version, model, and firmware.
Bumper does not care which exact domain is used, as long as the request reaches Bumper and is handled.

!!! note

    The app may dynamically retrieve service/domain information from
    `https://api-app.<region shard>.ecouser.net/api/appsvr/service/list`
    (for example `api-app.dc-eu.ww.ecouser.net`).
    Required domains can vary across models, regions, and firmware versions.

### Replacement Examples

Most domains follow patterns based on country or region codes:

- `{country}`: for `gl-{country}-api.ecovacs.com` and
  `gl-{country}-openapi.ecovacs.com`, use `gl-de-api.ecovacs.com` and
  `gl-de-openapi.ecovacs.com` for Germany. Country codes such as `us`, `de`, or
  `jp` appear here.
- `{region}`: for `portal-{region}.ecouser.net` in North America, use
  `portal-na.ecouser.net`. `{region}` may also be `eu`, `cn`, or `ww`.

### Summary

- ✅ **If your DNS supports wildcard or full-domain overrides**, use them to catch all subdomains at once.
- ❌ **If it does not**, manually define each used domain/subdomain.

---

## 💡 Known Domains

These are common domain patterns.
The exact hostnames depend on app version, account region, and device model.
Prefer wildcard DNS overrides when possible;
if your resolver cannot use wildcards, monitor DNS traffic and add the specific hostnames your device requests.

| Pattern                                                                                               | Purpose                                                                   |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `lb*.ecouser.net`                                                                                     | Load-balancer discovery                                                   |
| `portal*.ecouser.net`                                                                                 | Login and REST API                                                        |
| `gl-{country}-api.ecovacs.com`, `gl-{country}-openapi.ecovacs.com`                                    | Modern app API                                                            |
| `api-app*.ecouser.net`, `api-rop.dc-{region}.ww.ecouser.net`, `users-base.dc-{region}.ww.ecouser.net` | App v2+ REST APIs and accounts                                            |
| `msg*.ecouser.net`                                                                                    | XMPP                                                                      |
| `mq*.ecouser.net`, `jmq-ngiot-*.ecouser.net`                                                          | MQTT / NGIoT                                                              |
| `*.iot-as-mqtt.*.aliyuncs.com`, `*.itls.*.aliyuncs.com`                                               | Aliyun IoT MQTT endpoints (observed with app/NGIoT traffic)               |
| `kinesisvideo.{region}.amazonaws.com`, `*.kinesisvideo.{region}.amazonaws.com`                        | Observed in live-video/KVS experiments; not part of standard Bumper setup |
| `recommender.ecovacs.com`, `bigdata-*.ecovacs.com`, `sa-eu-datasink.ecovacs.com`                      | Optional telemetry/recommendation services                                |

## 🔒 Certificate and Trust Notes

Bumper's certificate covers many intercepted host patterns, but **SAN coverage
alone does not make a host work**: DNS must reach Bumper, the certificate must
be valid for that name, and the client must trust the CA on the path it uses.

Two paths can still refuse a user-installed CA: the app's MQTT pin and channels
with a native TLS stack (NGIoT, Aliyun IoT MQTT). See
[Certificates](certificates.md),
[App Certificate Unpinning](../internals/certificate-unpinning-app.md), and
[The app on the wire](../internals/authentication.md#the-app-on-the-wire).

---

## 🔍 Troubleshooting

- **App won't connect**: test overrides with `dig` or `nslookup` against your DNS server
  to confirm the Ecovacs domains resolve to your Bumper IP.
- **Partial redirects**: clear the device DNS cache or reboot the robot and used device.
- **IPv6 issues**: if your network uses IPv6, add corresponding AAAA records for each domain.
- **Pi-hole v6 ignores `02-bumper.conf`**: verify that `FTLCONF_misc.dnsmasq_d=true`
  (or the GUI equivalent) is enabled so FTL consumes `/etc/dnsmasq.d/`.

---

## 📚 Resources

- [OPNsense Unbound Host Overrides](https://docs.opnsense.org/manual/unbound.html)
- [dnsmasq address configuration](http://www.thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html#address)
- [Pi-hole documentation](https://docs.pi-hole.net/)
- [Pi-hole v6 + `dnsmasq.d` workaround](https://discourse.pi-hole.net/t/etc-dnsmasq-d-is-disabled-after-upgrading-to-v6/76059)
