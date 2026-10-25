# Environment Variables Overview

Bumper's behavior can be tailored by setting environment variables before startup.
Below is a list of all variables that the Python application reads, grouped by category.
Variables not listed here are hardcoded or not configurable via environment.

---

## ⏰ Timezone

| Variable        | Default | Description                                                                                                                                              |
| --------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TZ`            | `UTC`   | Timezone for scheduling and log timestamps. Set to any [IANA zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones), e.g., `Europe/Berlin`. |
| `SYNC_TIMEZONE` | `false` | Sync the server timezone offset to robots when they connect over MQTT.                                                                                   |

---

## ⚙️ Feature Flags

| Variable                        | Default                                  | Description                                                                                                                        |
| ------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `CA_CERT_API_ONLY_BUMPER_CERT`  | `false`                                  | If `true`, only the self-signed Bumper CA is served. If `false`, the bundle also carries the original system CA.                   |
| `USER_USERNAME_DEFAULT`         | `bumper`                                 | Username the local account is presented with.                                                                                      |
| `USER_NICKNAME_DEFAULT`         | `USER_USERNAME_DEFAULT`                  | Display name of the local account. Shown as the member name in the app.                                                            |
| `USER_MAIL_DEFAULT`             | `${USER_USERNAME_DEFAULT}@home.local`    | Mail address the local account is presented with.                                                                                  |
| `PHOTO_MAX_PER_DEVICE`          | `20`                                     | How many uploaded files are kept per robot, pictures and cleaned maps alike. The oldest are dropped on every new upload.           |
| `CLEAN_LOG_MAX_PER_DEVICE`      | `100`                                    | How many clean log entries are kept per robot. The oldest are dropped on every new one.                                            |
| `WEBVIEW_TRUSTED_HOST_SUFFIXES` | `ecovacs.com,ecovacs.cn,ecouser.net,...` | Hosts the app may open in a webview. The app ships the Ecovacs domains as a fallback, add the host this instance is reached under. |

---

## 📁 Paths & Files

| Variable             | Default                      | Description                                                                |
| -------------------- | ---------------------------- | -------------------------------------------------------------------------- |
| `BUMPER_DATA`        | `$PWD/data`                  | Directory for persistent data, uploads and caches.                         |
| `DB_FILE`            | `${BUMPER_DATA}/bumper.db`   | TinyDB database file. The file holds JSON, not SQL.                        |
| `BUMPER_ACCOUNT_KEY` | `${BUMPER_DATA}/account.key` | RSA key used to decrypt account fields the app encrypts. Mode `0600`.      |
| `BUMPER_CERTS`       | `$PWD/certs`                 | Directory for TLS certificate files.                                       |
| `BUMPER_VOICES`      | `${BUMPER_DATA}/voices`      | Directory for the voice files the robot downloads.                         |
| `BUMPER_CODEPUSH`    | `${BUMPER_DATA}/codepush`    | Directory for the CodePush packages the app downloads.                     |
| `BUMPER_CA_CERT`     | `${BUMPER_CERTS}/ca.crt`     | Path to the CA certificate. `BUMPER_CA` is accepted as a deprecated alias. |
| `BUMPER_CA_KEY`      | `${BUMPER_CERTS}/ca.key`     | Path to the CA private key.                                                |
| `BUMPER_CA_PEM`      | `${BUMPER_CERTS}/ca.pem`     | Path to the combined server key, server certificate and CA certificate.    |
| `BUMPER_CERT`        | `${BUMPER_CERTS}/bumper.crt` | Path to the server certificate.                                            |
| `BUMPER_KEY`         | `${BUMPER_CERTS}/bumper.key` | Path to the server private key.                                            |

---

## 🔐 Certificates

| Variable               | Default | Description                                                                                            |
| ---------------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `BUMPER_CA_VALID_DAYS` | `6669`  | CA certificate validity in days (about 18 years). Long duration for home-hosted self-signed stability. |
| `BUMPER_VALID_DAYS`    | `666`   | Server certificate validity in days (about 22 months). Practical rotation cycle for home management.   |
| `CERT_KEY_TYPE`        | `ec`    | Key algorithm. Accepts only `ec` (P-256 elliptic curve) or `rsa`.                                      |
| `CERT_RSA_KEY_SIZE`    | `2048`  | RSA key size in bits. Must be `2048` to `4096`. Ignored for EC keys.                                   |

---

## 🔒 Authentication

| Variable                         | Default          | Description                                                                                  |
| -------------------------------- | ---------------- | -------------------------------------------------------------------------------------------- |
| `TOKEN_VALIDITY_SECONDS`         | `2592000`        | Portal-token session lifetime in seconds (30 days).                                          |
| `ACCESS_TOKEN_VALIDITY_SECONDS`  | `1800`           | OAuth access JWT lifetime in seconds (30 minutes).                                           |
| `REFRESH_TOKEN_VALIDITY_SECONDS` | `2592000`        | OAuth refresh JWT lifetime in seconds (30 days).                                             |
| `TOKEN_JWT_ALG`                  | Follows key type | Algorithm used to sign app tokens. Defaults to `ES256` for EC keys and `RS256` for RSA keys. |

Bumper does not verify Ecovacs request signatures. See [Authentication](../internals/authentication.md) for the full flow.

---

## 🌐 Networking

| Variable                 | Default                      | Description                                                                                                                                                                                    |
| ------------------------ | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BUMPER_LISTEN`          | Auto-detected via system DNS | IP address or hostname to bind all server listeners (Web, MQTT, XMPP).                                                                                                                         |
| `BUMPER_ANNOUNCE_IP`     | `${BUMPER_LISTEN}`           | IP advertised to robots. If `0.0.0.0`, set explicitly.                                                                                                                                         |
| `WEB_SERVER_HTTPS_PORT`  | `443`                        | Port for the HTTPS web UI and API.                                                                                                                                                             |
| `WEB_SERVER_LISTEN_PORT` | `8007`                       | Port for the plain HTTP web UI and API.                                                                                                                                                        |
| `MQTT_LISTEN_PORT`       | `1883`                       | Plain MQTT listener.                                                                                                                                                                           |
| `MQTT_LISTEN_PORT_TLS`   | `8883`                       | TLS MQTT listener.                                                                                                                                                                             |
| `XMPP_LISTEN_PORT_TLS`   | `5223`                       | TLS XMPP listener.                                                                                                                                                                             |
| `HELPER_BOT_TIMEOUT`     | `10`                         | Seconds the helper bot waits for a robot to answer. The app gives up on a request after 15 seconds, so a longer wait is never seen by it.                                                      |
| `CODEPUSH_LOCAL_PACKAGE` | `false`                      | Serve the CodePush package from this server instead of the cloud. The app then downloads it from the host of the CodePush service, which has to be one that the DNS override points at Bumper. |

---

## 🚦 Logging & Debugging

| Variable                              | Default | Description                                                            |
| ------------------------------------- | ------- | ---------------------------------------------------------------------- |
| `DEBUG_BUMPER_LEVEL`                  | `INFO`  | Log level (`NOTSET`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `DEBUG_BUMPER_VERBOSE`                | `1`     | Verbose output per log line (integer `0`, `1`, `2`).                   |
| `DEBUG_LOGGING_API_REQUEST`           | `false` | Log incoming API requests.                                             |
| `DEBUG_LOGGING_API_REQUEST_MISSING`   | `false` | Log requests that no route matches.                                    |
| `DEBUG_LOGGING_XMPP_REQUEST`          | `false` | Log XMPP requests before internal changes.                             |
| `DEBUG_LOGGING_XMPP_REQUEST_REFACTOR` | `false` | Log XMPP requests after internal changes.                              |
| `DEBUG_LOGGING_XMPP_RESPONSE`         | `false` | Log XMPP server responses.                                             |
| `DEBUG_LOGGING_SA_RESULT`             | `false` | Log service-autonomy outputs from API requests by `/sa`.               |

---

## 🔗 Proxy & Forwarding

| Variable                | Default | Description                                                                 |
| ----------------------- | ------- | --------------------------------------------------------------------------- |
| `BUMPER_PROXY_MQTT`     | `false` | Forward MQTT traffic to the Ecovacs cloud.                                  |
| `BUMPER_PROXY_WEB`      | `false` | Forward web traffic to the Ecovacs cloud.                                   |
| `PROXY_PUBLISH_TIMEOUT` | `10`    | Seconds a proxied MQTT publish may wait before it is reported as timed out. |

---

## 🚢 Docker Compose & Swarm Variables

These additional environment variables are used in the compose files to control service deployment and container behavior.

| Variable                        | Default                | Description                                                                          |
| ------------------------------- | ---------------------- | ------------------------------------------------------------------------------------ |
| `NODE_ROLE`                     | `manager`              | Docker Swarm role constraint for service placement (`manager` or `worker`).          |
| `NETWORK_MODE`                  | `bridge`               | Docker network driver (`bridge` or `overlay`).                                       |
| `RESOURCES_LIMITS_CPUS`         | `0.25`                 | CPU limit per container.                                                             |
| `RESOURCES_LIMITS_MEMORY`       | `250m`                 | Memory limit per container.                                                          |
| `RESOURCES_RESERVATIONS_CPUS`   | `0.001`                | CPU reservation per container.                                                       |
| `RESOURCES_RESERVATIONS_MEMORY` | `32m`                  | Memory reservation per container.                                                    |
| `VERSION_BUMPER`                | `latest`               | Bumper image tag to deploy. The image reports its build version under the same name. |
| `VERSION_NGNIX`                 | `1.29-alpine3.22-slim` | NGINX image tag for the reverse proxy.                                               |
| `TZ`                            | `Europe/Berlin`        | Timezone inside containers (binds to host timezone).                                 |
| `BUMPER_ANNOUNCE_IP`            | _required_             | IP address advertised to robots. Falls back to auto-detection if unset.              |
| `BUMPER_LISTEN`                 | `0.0.0.0`              | Bind interface inside the container for Bumper listeners.                            |
| `DEBUG_BUMPER_LEVEL`            | `INFO`                 | Logging level inside containers.                                                     |
| `DEBUG_BUMPER_VERBOSE`          | `1`                    | Verbose detail per log line inside containers.                                       |
