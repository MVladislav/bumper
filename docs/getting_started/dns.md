# DNS Configuration for Bumper

To intercept and redirect traffic from Ecovacs robots and the official app to
your local **Bumper** server, configure your network’s DNS resolver to override
specific Ecovacs domains to your server’s IP.

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
4. Repeat for each domain pattern:
    - `*.ecouser.com`
    - `*.ecovacs.com`
    - `*.ecouser.net`
    - `*.ecovacs.net`
5. Click **Apply** to reload Unbound.

> These wildcard entries catch all subdomains under the specified domain.

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

Replace `<BUMPER_SERVER_IP>` with your server’s local IP (e.g. `192.168.1.100`).

**Apply changes:**

- **dnsmasq**: `sudo systemctl reload dnsmasq`
- **Pi-hole**: `pihole restartdns` or via the web UI

### ⚠️ Pi-hole v6 and `dnsmasq.d`

Pi-hole v6 does **not** ingest custom configs in `/etc/dnsmasq.d/` by default; this behavior is disabled in FTL. [discourse.pi-hole](https://discourse.pi-hole.net/t/etc-dnsmasq-d-is-disabled-after-upgrading-to-v6/76059)
You must explicitly re-enable it:

- **ENV**: add as environment variable:
    - `FTLCONF_misc.dnsmasq_d=true`
- **Via GUI**: in the Pi-hole web UI, go to **Settings > All settings page - Miscellaneous** and enable the option.

Without this, custom `02-bumper.conf`-style entries will be silently ignored, explaining why DNS redirects may appear not to work.

---

## 📋 Notes on Domain Patterns

If overriding DNS for top-level domains (like `*.ecovacs.com`) isn’t supported in your DNS setup,
you’ll need to manually configure each relevant subdomain used by the app or robot to point to your **Bumper** server.

EcoVacs robots and the companion app connect to a variety of domains depending on the country or region selected during setup.
The Bumper project doesn’t care which exact domain is used—as long as the request is forwarded, it will be intercepted correctly.

> 🧠 The app dynamically retrieves its domain list from the endpoint:  
> `https://{region}.ecouser.net/api/appsvr/service/list`  
> This means the required domains may vary across models, regions, and firmware versions.

### Replacement Examples

Most domains follow patterns based on country or region codes:

- `{countrycode}`
    - If you see `eco-{countrycode}-api.ecovacs.com` and you're in the US/North America, use:
      `eco-us-api.ecovacs.com`
    - **Note:** `{countrycode}` may also be region codes like `EU`, `WW`, or `CN`.
- `{region}`
    - If you see `portal-{region}.ecouser.net` and you're in North America, use:
      `portal-na.ecouser.net`
    - **Note:** `{region}` values may also include `eu`, `cn`, or `ww`.

### Summary

- ✅ **If your DNS supports wildcard or full-domain overrides**, use them to catch all subdomains at once.
- ❌ **If it does not**, you must manually define each used domain/subdomain to ensure proper redirection.

---

## 💡 Known Domains

| Address                                  | Description                        |
| :--------------------------------------- | :--------------------------------- |
| `lb-{countrycode}.ecovacs.net`           | Load-balancer checked by app/robot |
| `lb-{countrycode}.ecouser.net`           | Load-balancer checked by app/robot |
| `lbus.ecouser.net`                       | Load-balancer checked by app/robot |
| `lb{countrycode}.ecouser.net`            | Load-balancer checked by app/robot |
| `eco-{countrycode}-api.ecovacs.com`      | Used for login                     |
| `gl-{countrycode}-api.ecovacs.com`       | Used by EcoVacs Home app           |
| `gl-{countrycode}-openapi.ecovacs.com`   | Used by EcoVacs Home app           |
| `portal.ecouser.net`                     | Used for login and REST API        |
| `portal-{countrycode}.ecouser.net`       | Used for login and REST API        |
| `portal-{region}.ecouser.net`            | Used for login and REST API        |
| `portal-ww.ecouser.net`                  | Used for various REST APIs         |
| `msg-{countrycode}.ecouser.net`          | Used for XMPP                      |
| `msg-{region}.ecouser.net`               | Used for XMPP                      |
| `msg-ww.ecouser.net`                     | Used for XMPP                      |
| `mq-{countrycode}.ecouser.net`           | Used for MQTT                      |
| `mq-{region}.ecouser.net`                | Used for MQTT                      |
| `mq-ww.ecouser.net`                      | Used for MQTT                      |
| `recommender.ecovacs.com`                | Used by EcoVacs Home app           |
| `bigdata-international.ecovacs.com`      | Telemetry/tracking                 |
| `bigdata-northamerica.ecovacs.com`       | Telemetry/tracking                 |
| `bigdata-europe.ecovacs.com`             | Telemetry/tracking                 |
| `bigdata-{unknown regions}.ecovacs.com`  | Telemetry/tracking                 |
| `api-app.ww.ecouser.net`                 | App v2+ API                        |
| `api-app.dc-{region}.ww.ecouser.net`     | App v2+ API                        |
| `users-base.dc-{region}.ww.ecouser.net`  | App v2+ accounts                   |
| `jmq-ngiot-{region}.dc.ww.ecouser.net`   | App v2+ MQTT                       |
| `api-rop.dc-{region}.ww.ecouser.net`     | App v2+ API                        |
| `jmq-ngiot-{region}.area.ww.ecouser.net` | App v2+ MQTT                       |

### Domains with Known IPs

| Domain                                   | IP             | Port |
| :--------------------------------------- | :------------- | :--- |
| api-app.dc-as.ww.ecouser.net             | 13.213.212.149 | 443  |
| api-app.dc-eu.ww.ecouser.net             | 52.58.74.156   | 443  |
| api-app.ww.ecouser.net                   | 52.58.74.156   | 443  |
| portal-ww.ecouser.net                    | 3.68.172.231   | 443  |
| users-base.dc-eu.ww.ecouser.net          | 52.58.74.156   | 443  |
| jmq-ngiot-eu.dc.ww.ecouser.net           | 3.127.110.57   | 8883 |
| msg-eu.ecouser.net                       | 18.196.130.16  | 5223 |
| api-base.robotww.ecouser.net             | 13.56.199.251  | 443  |
|                                          |                |      |
| gl-de-api.ecovacs.com                    | 3.123.55.28    | 443  |
| gl-de-api.ecovacs.com                    | 52.58.23.18    | 443  |
| gl-de-openapi.ecovacs.com                | 3.123.55.28    | 443  |
| gl-us-api.ecovacs.com                    | 52.10.83.13    | 443  |
| gl-us-api.ecovacs.com                    | 54.186.31.147  | 443  |
| gl-us-pub.ecovacs.com                    | 108.138.7.23   | 443  |
| gl-us-pub.ecovacs.com                    | 108.138.7.64   | 443  |
| gl-us-pub.ecovacs.com                    | 13.224.222.120 | 443  |
| recommender.ecovacs.com                  | 116.62.93.217  | 443  |
| sa-eu-datasink.ecovacs.com               | 18.193.135.83  | 443  |
| sa-eu-datasink.ecovacs.com               | 3.123.96.17    | 443  |
| site-static.ecovacs.com                  | 13.32.27.60    | 443  |
|                                          |                |      |
| living-account.eu-central-1.aliyuncs.com | 8.211.2.91     | 443  |
| sgp-sdk.openaccount.aliyun.com           | 8.219.176.88   | 443  |

### Current Domains with TLS Errors

| Domain                                           | IP             | Port |
| :----------------------------------------------- | :------------- | :--- |
| a2JaaxoKXLq.iot-as-mqtt.cn-shanghai.aliyuncs.com | 106.14.207.159 |      |
| jmq-ngiot-na.dc.robotww.ecouser.net              | 184.72.41.195  |      |
| jmq-ngiot-eu.dc.robotww.ecouser.net              | 63.176.16.162  |      |
| public.itls.eu-central-1.aliyuncs.com            | 8.209.119.138  |      |

> 🧩 This list will grow as more regions and device behaviors are observed.
> Monitor DNS traffic if your robot or app isn’t connecting as expected.

---

## 🔍 Troubleshooting

- **App won’t connect**: Test overrides with `dig` or `nslookup` against your DNS server to confirm the Ecovacs domains resolve to your Bumper IP.
- **Partial redirects**: Clear used device DNS cache or reboot the robot and used device.
- **IPv6 issues**: If your network uses IPv6, add corresponding AAAA records for each domain.
- **Pi-hole v6 confusion ([#165](https://github.com/MVladislav/bumper/issues/165))**: If `02-bumper.conf` changes have no effect, verify that `FTLCONF_misc.dnsmasq_d=true` (or the GUI equivalent) is enabled so FTL consumes `/etc/dnsmasq.d/`. [discourse.pi-hole](https://discourse.pi-hole.net/t/etc-dnsmasq-d-is-disabled-after-upgrading-to-v6/76059)

---

## 📚 Resources

- [OPNsense Unbound Host Overrides](https://docs.opnsense.org/manual/unbound.html)
- [dnsmasq address configuration](http://www.thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html#address)
- [Pi-hole documentation](https://docs.pi-hole.net/)
- [Pi-hole v6 + `dnsmasq.d` disablement workaround](https://discourse.pi-hole.net/t/etc-dnsmasq-d-is-disabled-after-upgrading-to-v6/76059)
