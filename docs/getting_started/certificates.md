# Generating Certificates for Bumper

The `scripts/create-cert.sh` helper will generate all necessary certificates into the `certs/` directory for both Bumper and mitmproxy.

---

## 📂 Script Location & Overview

- **Path**: `scripts/create-cert.sh`
- **Purpose**:
    - Create a root CA (`ca.key` + `ca.crt`)
    - Issue a server certificate (`bumper.key` + `bumper.crt`)
    - Produce a combined PEM (`ca.pem`) for mitmproxy by merging CA and server certs

> If you already possess your own certs, simply place them in `certs/`:
>
> - `ca.crt`, `bumper.key`, `bumper.crt` for Bumper
> - `ca.pem` for mitmproxy

---

## 🚀 Execute the Script

```sh
$./scripts/create-cert.sh
```

On success, the `certs/` directory contains:

- `ca.key`  – Root CA private key
- `ca.crt`  – Root CA certificate
- `bumper.key` – Server private key
- `bumper.crt` – Server certificate
- `ca.pem`  – Combined CA+server cert (for mitmproxy)

> The script skips existing files to protect your keys.

---

## ⚙️ Using Certificates

### Bumper Application

Configure Bumper to load certificates (defaults shown):

```env
BUMPER_CERTS=certs
BUMPER_CA=ca.crt
BUMPER_CERT=bumper.crt
BUMPER_KEY=bumper.key
```

Or point directly to full paths:

```env
BUMPER_CA_PATH=certs/ca.crt
BUMPER_CERT_PATH=certs/bumper.crt
BUMPER_KEY_PATH=certs/bumper.key
```

### mitmproxy

Mount `ca.pem` into your mitmproxy container or CLI:

```sh
$docker run --rm -it \
  -v $PWD/certs/ca.pem:/home/mitm/ca.pem:ro \
  mitmproxy/mitmproxy mitmweb \
    --certs '*=/home/mitm/ca.pem'
```

---

## 🐍 Python Configuration (Advanced)

Bumper’s Python `Config` class reads these env vars if set:

| Variable       | Default      | Description            |
| -------------- | ------------ | ---------------------- |
| `BUMPER_CERTS` | `./certs`    | Certificates directory |
| `BUMPER_CA`    | `ca.crt`     | CA cert filename       |
| `BUMPER_CERT`  | `bumper.crt` | Server cert filename   |
| `BUMPER_KEY`   | `bumper.key` | Server key filename    |

> Note: `ca.pem` is only needed by mitmproxy; Bumper uses individual CRT/KEY files.
