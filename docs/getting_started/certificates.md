# 🔒 Certificates for Bumper

Bumper serves TLS for the app, robots, and its web UI. The certificates are
self-signed: clients must trust Bumper's CA, and the server certificate must
cover the Ecovacs hostnames clients connect to.

## 📦 Files

Both creation methods produce the same files:

| File         | Created by                                                | Purpose                                                          |
| ------------ | --------------------------------------------------------- | ---------------------------------------------------------------- |
| `ca.key`     | `scripts/certs/create-cert.sh` or `bumper/utils/certs.py` | Root CA private key                                              |
| `ca.crt`     | `scripts/certs/create-cert.sh` or `bumper/utils/certs.py` | Root CA certificate - install/trust this on app and clients      |
| `bumper.key` | `scripts/certs/create-cert.sh` or `bumper/utils/certs.py` | Server private key                                               |
| `bumper.crt` | `scripts/certs/create-cert.sh` or `bumper/utils/certs.py` | Server certificate signed by the CA                              |
| `ca.pem`     | `scripts/certs/create-cert.sh` or `bumper/utils/certs.py` | Server key + server certificate + CA certificate (for mitmproxy) |

Default key type is EC. Use RSA when a robot requires it: `--rsa` with the
script, or `CERT_KEY_TYPE=rsa` with startup generation. The SAN list is defined
by each implementation (`scripts/certs/create-cert.sh` and
`bumper/utils/certs.py`).

## 🧰 Option 1 - Create certificates with the host script {#host-certs}

The script uses OpenSSL on the host and writes files to `$PWD/certs`:

```sh
bash scripts/certs/create-cert.sh

# RSA instead of EC
bash scripts/certs/create-cert.sh --rsa
```

Behavior (idempotent):

- if `ca.crt` or `ca.key` is missing, it creates a new CA and a new server
  certificate;
- if the CA exists but `bumper.crt` or `bumper.key` is missing, it creates a
  new server certificate and keeps the existing CA (clients that already trust
  the CA keep working);
- `ca.pem` is rebuilt if it is missing.

Use this when you want to create or rotate certificates yourself before
starting Bumper.

## 🐍 Option 2 - Let Bumper generate certificates at startup {#startup-certs}

`bumper.utils.certs.generate_certificates()` runs during Bumper startup, before
services listen. It writes the same five files to `BUMPER_CERTS` (default
`$PWD/certs` / `/bumper/certs` in containers) when the directory is writable.

```sh
BUMPER_CERTS=$PWD/certs uv run --active bumper
```

Behavior:

- if `ca.crt`, `bumper.crt`, and `bumper.key` all exist, generation is skipped
  (existing certificates are kept);
- `ca.key` is not part of that existence check, so removing only `ca.key` does
  not trigger a new CA;
- if only `ca.pem` is missing, it is rebuilt from the existing key and
  certificates;
- changing `CERT_KEY_TYPE` later does not convert an existing certificate set.

Startup generation requires a writable certificates directory owned by (or
writable for) the Bumper process (uid/gid `1000` in the container image). The
checked-in Docker image starts as root, repairs ownership of `/bumper/data` and
`/bumper/certs` when it can (`CAP_CHOWN`), then drops to `bumper`.

### Generation settings

| Variable               | Default   | Effect                                            |
| ---------------------- | --------- | ------------------------------------------------- |
| `BUMPER_CERTS`         | `./certs` | Directory for generated files                     |
| `CERT_KEY_TYPE`        | `ec`      | `ec` (ECDSA P-256) or `rsa`                       |
| `CERT_RSA_KEY_SIZE`    | `2048`    | RSA key size when `CERT_KEY_TYPE=rsa` (2048-4096) |
| `BUMPER_CA_VALID_DAYS` | `6669`    | CA validity in days                               |
| `BUMPER_VALID_DAYS`    | `666`     | Server certificate validity in days               |

Individual paths can be overridden with `BUMPER_CA_CERT`, `BUMPER_CA_KEY`,
`BUMPER_CA_PEM`, `BUMPER_CERT`, and `BUMPER_KEY`.

## 🐳 Checked-in Docker/Compose behavior

The checked-in `docker-compose.yaml` and `docker-compose-traefik.yaml` load
`ca.crt`, `bumper.crt`, and `bumper.key` as Docker configs from `$PWD/certs/*`
and mount them read-only at `/bumper/certs`. The source files must exist before
deployment:

```sh
bash scripts/certs/create-cert.sh
# add --rsa if your robot requires RSA keys
```

After creating them, install `certs/ca.crt` on devices/clients that need to
trust Bumper.

Bumper's [startup generation](#startup-certs) needs a writable `/bumper/certs`
directory, so it does not run with these read-only config mounts. For a custom
deployment where you want Bumper to generate certificates, mount a writable
directory/volume at `/bumper/certs` instead of read-only config files. In
Docker Swarm, host bind mounts are node-local; ensure the directory exists and
is writable on the node that runs the task, or pre-create certificates with the
host script (recommended for the checked-in Swarm files).

## 📂 Custom certificates

To use your own CA and server certificate, place files in the certificates
directory before starting Bumper:

- `ca.crt`, `bumper.key`, `bumper.crt` for Bumper
- `ca.pem` for mitmproxy (optional)

The server certificate must include the Ecovacs hostnames and local addresses
clients use. `ca.pem` contains the server private key; treat it as a secret and
use it only for local tooling such as mitmproxy.

## 🧪 mitmproxy

Mount `ca.pem` into mitmproxy:

```sh
docker run --rm -it \
  -v $PWD/certs/ca.pem:/home/mitm/ca.pem:ro \
  mitmproxy/mitmproxy mitmweb \
    --certs '*=/home/mitm/ca.pem'
```

`ca.pem` is only needed by mitmproxy; Bumper uses the individual CRT/KEY files.
