# Certificates for Bumper

Bumper requires TLS certificates to communicate securely with Ecovacs devices and apps.

---

## 🔄 Automatic Generation

**Bumper generates certificates as part of its normal startup** if the required
files are missing. This happens automatically; no manual generation command is
needed. The Python startup and helper script use the same certificate filenames in
the `certs/` directory relative to their working directory.

You can also create the files ahead of startup with the helper:

```sh
bash scripts/certs/create-cert.sh
```

For the checked-in Compose and Swarm files, there is an additional constraint:
they load the certificate files as host-backed Docker configs before starting the
Bumper container. Those host files must exist before deployment, so create them
with the helper above when using these files. Bumper's automatic generation still
applies to startup modes where it can write to its certificate directory.

For a robot that requires RSA keys, set `CERT_KEY_TYPE=rsa` when Bumper generates a
new certificate set. Bumper keeps an existing certificate set; changing
`CERT_KEY_TYPE` does not convert certificates that were already generated.

---

## 📂 Generated Files

When certificate generation runs, Bumper creates the following files in `certs/`:

| File         | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| `ca.key`     | Root CA private key                                           |
| `ca.crt`     | Root CA certificate                                           |
| `bumper.key` | Server private key                                            |
| `bumper.crt` | Server certificate                                            |
| `ca.pem`     | Server key, server certificate and CA certificate in one file |

> Bumper skips generation if all certificate files already exist.

`ca.pem` contains the server private key. Treat it as a secret and do not share
it; it is only meant for a local proxy such as mitmproxy.

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
BUMPER_CA_KEY=certs/ca.key
BUMPER_CA_PEM=certs/ca.pem
BUMPER_CERT=certs/bumper.crt
BUMPER_KEY=certs/bumper.key
```

### mitmproxy

Mount `ca.pem` into your mitmproxy container or CLI:

```sh
docker run --rm -it \
  -v $PWD/certs/ca.pem:/home/mitm/ca.pem:ro \
  mitmproxy/mitmproxy mitmweb \
    --certs '*=/home/mitm/ca.pem'
```

> Note: `ca.pem` is only needed by mitmproxy; Bumper uses individual CRT/KEY files.
