# Certificates for Bumper

Bumper requires TLS certificates to communicate securely with Ecovacs devices and apps.

---

## 🔄 Automatic Generation

**Bumper automatically generates certificates on first startup** if they don't exist. Simply start Bumper and it will create all necessary certificates in the `certs/` directory.

No manual steps required - this is the recommended approach.

---

## 📂 Generated Files

On first startup, Bumper creates the following files in `certs/`:

| File         | Description                             |
| ------------ | --------------------------------------- |
| `ca.key`     | Root CA private key                     |
| `ca.crt`     | Root CA certificate                     |
| `bumper.key` | Server private key                      |
| `bumper.crt` | Server certificate                      |
| `ca.pem`     | Combined CA+server cert (for mitmproxy) |

> Bumper skips generation if all certificate files already exist.

---

## 🔧 Custom Certificates

If you prefer to use your own certificates, place them in the `certs/` directory before starting Bumper:

- `ca.crt`, `bumper.key`, `bumper.crt` for Bumper
- `ca.pem` for mitmproxy (optional)

---

## ⚙️ Configuration

### Environment Variables

Configure certificate paths via environment variables (defaults shown):

```env
BUMPER_CERTS=$PWD/certs
```

Or point directly to full paths:

```env
BUMPER_CA_CERT=certs/ca.crt
BUMPER_CERT=certs/bumper.crt
BUMPER_KEY=certs/bumper.key
```

### mitmproxy

Mount `ca.pem` into your mitmproxy container or CLI:

```sh
$docker run --rm -it \
  -v $PWD/certs/ca.pem:/home/mitm/ca.pem:ro \
  mitmproxy/mitmproxy mitmweb \
    --certs '*=/home/mitm/ca.pem'
```

> Note: `ca.pem` is only needed by mitmproxy; Bumper uses individual CRT/KEY files.
