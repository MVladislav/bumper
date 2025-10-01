# Environment Variables Overview

Bumper’s behavior can be tailored by setting environment variables before startup.
Below is a list of all variables that the Python application reads, grouped by category.
Variables not listed here are hardcoded or not configurable via environment.

---

## ⏰ Timezone

| Variable | Default | Description                                                                                                                                              |
| -------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TZ`     | `UTC`   | Timezone for scheduling and log timestamps. Set to any [IANA zone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones), e.g., `Europe/Berlin`. |

---

## ⚙️ Feature Flags

| Variable                       | Default | Description                                                                                                                                           |
| ------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CA_CERT_API_ONLY_BUMPER_CERT` | `False` | If `true`, **only** the **self-signed CA** is served. If `false`, the **bundle** includes both the **self-signed CA** and the **original system CA**. |

---

## 📁 Paths & Files

| Variable       | Default                    | Description                                           |
| -------------- | -------------------------- | ----------------------------------------------------- |
| `BUMPER_DATA`  | `$PWD/data`                | Directory for persistent data (database, caches).     |
| `DB_FILE`      | `${BUMPER_DATA}/bumper.db` | Path to SQLite database file. Overrides default.      |
| `BUMPER_CERTS` | `$PWD/certs`               | Directory for TLS certificate files.                  |
| `BUMPER_CA`    | `ca.crt`                   | Filename of CA certificate inside `BUMPER_CERTS`.     |
| `BUMPER_CERT`  | `bumper.crt`               | Filename of server certificate inside `BUMPER_CERTS`. |
| `BUMPER_KEY`   | `bumper.key`               | Filename of server private key inside `BUMPER_CERTS`. |

---

## 🔒 Authentication

| Variable        | Default | Description                                                             |
| --------------- | ------- | ----------------------------------------------------------------------- |
| `TOKEN_JWT_ALG` | `ES256` | JWT algorithm to be used, depends on the bumper certificate you create. |

---

## 🌐 Networking

| Variable                | Default                      | Description                                                            |
| ----------------------- | ---------------------------- | ---------------------------------------------------------------------- |
| `BUMPER_LISTEN`         | Auto-detected via system DNS | IP address or hostname to bind all server listeners (Web, MQTT, XMPP). |
| `BUMPER_ANNOUNCE_IP`    | `${BUMPER_LISTEN}`           | IP advertised to robots. If `0.0.0.0`, set explicitly.                 |
| `WEB_SERVER_HTTPS_PORT` | `443`                        | Port for HTTPS web UI.                                                 |

---

## 🚦 Logging & Debugging

| Variable                                | Default | Description                                                       |
| --------------------------------------- | ------- | ----------------------------------------------------------------- |
| `DEBUG_BUMPER_LEVEL`                    | `INFO`  | Log level (`NOTSET`,`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`). |
| `DEBUG_BUMPER_VERBOSE`                  | `1`     | Verbose output per log line (integer `0`,`1`,`2`).                |
| `DEBUG_LOGGING_API_REQUEST`             | `False` | Log incoming API requests.                                        |
| `DEBUG_LOGGING_API_REQUEST_MISSING`     | `False` | Log missing API parameters/details.                               |
| `DEBUG_LOGGING_XMPP_REQUEST_ORIGINAL`   | `False` | Log XMPP request before internal changed.                         |
| `DEBUG_LOGGING_XMPP_REQUEST_REFACTORED` | `False` | Log XMPP request after internal changed.                          |
| `DEBUG_LOGGING_XMPP_RESPONSE`           | `False` | Log XMPP server responses.                                        |
| `DEBUG_LOGGING_SA_RESULT`               | `False` | Log service-autonomy outputs from API requests by `/sa`.          |

---

## 🔗 Proxy & Forwarding

| Variable            | Default | Description                               |
| ------------------- | ------- | ----------------------------------------- |
| `BUMPER_PROXY_MQTT` | `False` | Enable built‑in MQTT proxy functionality. |
| `BUMPER_PROXY_WEB`  | `False` | Enable built‑in HTTP proxy functionality. |

---

## 🚢 Docker Compose & Swarm Variables

These additional environment variables are used in the `docker-compose.yml` and Swarm stack to control service deployment and container behavior.

| Variable                        | Default                  | Description                                                                 |
| ------------------------------- | ------------------------ | --------------------------------------------------------------------------- |
| `NODE_ROLE`                     | `manager`                | Docker Swarm role constraint for service placement (`manager` or `worker`). |
| `NETWORK_MODE`                  | `bridge`                 | Docker network driver (`bridge` or `overlay`).                              |
| `RESOURCES_LIMITS_CPUS`         | `0.25`                   | CPU limit per container.                                                    |
| `RESOURCES_LIMITS_MEMORY`       | `250m`                   | Memory limit per container.                                                 |
| `RESOURCES_RESERVATIONS_CPUS`   | `0.001`                  | CPU reservation per container.                                              |
| `RESOURCES_RESERVATIONS_MEMORY` | `32m`                    | Memory reservation per container.                                           |
| `VERSION_BUMPER`                | `develop`                | Bumper image tag to deploy (branch, release, or tag).                       |
| `VERSION_NGNIX`                 | `1.27.4-alpine3.21-slim` | NGINX image tag for the reverse proxy.                                      |
| `TZ`                            | `Europe/Berlin`          | Timezone inside containers (binds to host timezone).                        |
| `BUMPER_ANNOUNCE_IP`            | _required_               | IP address advertised to robots. Falls back to auto-detection if unset.     |
| `BUMPER_LISTEN`                 | `0.0.0.0`                | Bind interface inside the container for Bumper listeners.                   |
| `BUMPER_DEBUG_LEVEL`            | `INFO`                   | Logging level inside containers.                                            |
| `BUMPER_DEBUG_VERBOSE`          | `1`                      | Verbose log output level inside containers.                                 |
