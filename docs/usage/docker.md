# Docker

Manage Bumper via Docker-pull the official image, deploy with Compose or Swarm, build custom images, or run directly.

---

## 🔧 Prerequisites

Prepare TLS certificates and minimal environment variables before any deployment:

**TLS certificates**:

Bumper automatically generates certificates on first startup. Alternatively, place your own certs in `certs/ca.crt`, `certs/bumper.crt`, `certs/bumper.key`.

**Environment variables**:

Create a `.env` file with at least the following:

```env
NETWORK_MODE=overlay        # by default "bridge"

# Needs to be set when running with Docker; default is auto-detected from socket
BUMPER_ANNOUNCE_IP=192.168.0.100  # your server's public/local IP
```

Full environment variable reference: [Environment Variables](../configuration/environment.md)

---

## ✨ Pull the Official Image

```sh
docker pull ghcr.io/mvladislav/bumper:develop
```

See the package on GitHub Container Registry [here](https://github.com/MVladislav/bumper/pkgs/container/bumper).

---

## 🚀 Docker Swarm Deployment

**Step 1 - Clone the repository**

```sh
git clone https://github.com/MVladislav/bumper.git
cd bumper
```

**Step 2 - Initiate Docker in Swarm mode**

```sh
docker swarm init
```

**Step 3 - Start services**

> alias for [docker-swarm](https://github.com/MVladislav/.dotfiles/blob/0b069b6a8435a43037789d8b5c4e1c0c65c6a142/zsh/profile-append#L146)

```sh
docker-swarm-compose deebot      # alias for Docker Swarm Compose
# or
docker compose up -d             # standard Docker Compose
```

**Step 4 - Access the UI**

Visit `https://ecovacs.net/` in your browser.

---

## 🗣️ Voice Files

The robot can change its voice language, but it downloads the new voice from
Bumper first. The files are fetched from the Ecovacs cloud with
[`scripts/update-eco-voices.sh`](../development/static-data-update.md) and are
not part of the image.

They belong in the voice directory of the deployment, which is
`/bumper/data/voices` inside the container. The data directory is a volume in
every deployment style, so the files either live in that volume or are copied
into it:

```sh
docker cp ./data/voices/. <container>:/bumper/data/voices/
```

With a swarm the volume is shared between the nodes, so the files have to be
on every node that can run a task. `BUMPER_VOICES` points the server at
another directory.

Bumper reports what it found at startup:

```text
INFO :: bumper.web.server - Voice files :: 13 in '/bumper/data/voices'
```

Without the files the robot keeps the language it has. The rest of the app is unaffected.

---

## 🛠 Build a Custom Image

**Step 1 - Clone the repository** (if not already done)

```sh
git clone https://github.com/MVladislav/bumper.git
cd bumper
```

**Step 2 - Build**

```sh
docker build -t mvladislav/bumper .
```

Requires Docker ≥17.09 or Podman.

---

## 🎯 Direct Docker Run

**Step 1 - Create a Docker volume**

```sh
docker volume create bumper_data
```

(Or use a host directory: `-v /path/to/data:/bumper/data`.)

**Step 2 - Run the container**

```sh
docker run -it \
  --mount source=bumper_data,target=/bumper/data \
  -p 443:443 -p 8007:8007 -p 8883:8883 -p 5223:5223 \
  --name bumper \
  mvladislav/bumper
```

- **Volumes**: uses Docker volume `bumper_data`; replace with `-v /host/path:/bumper/data` for a host mount.
- **Ports**: 443, 8007, 8883, 5223

---

_For advanced Docker parameters (resource limits, secrets, configs), see the [Environment Variables](../configuration/environment.md)._
