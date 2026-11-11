# 🐳 Deploy Bumper

Manage Bumper with Docker: pull the official image, deploy with Compose or Swarm, build custom images, or run directly.

---

## 🔧 Prerequisites

**TLS certificates**

The checked-in `docker-compose.yaml` and `docker-compose-traefik.yaml` load
`ca.crt`, `bumper.crt`, and `bumper.key` from `$PWD/certs/*` as read-only Docker
configs, so the files must exist before you deploy. Create them, then install
`certs/ca.crt` on the clients:

```sh
bash scripts/certs/create-cert.sh
# add --rsa if your robot requires RSA keys
```

Key types, SANs, and certificate generation are covered in
[Certificates](../getting_started/certificates.md).

**Environment variables**:

Create a `.env` file with at least the following:

```env
# 'overlay' for Docker Swarm, 'bridge' for plain Docker Compose
NETWORK_MODE=overlay

# required by the Compose file
BUMPER_ANNOUNCE_IP=192.168.0.100  # your server's local IP
```

Full environment variable reference: [Environment Variables](../configuration/environment.md)

---

## ✨ Pull the Official Image

```sh
docker pull ghcr.io/mvladislav/bumper:latest
```

See the package on GitHub Container Registry [here](https://github.com/MVladislav/bumper/pkgs/container/bumper).

---

## 👤 Container User

Bumper runs as the unprivileged user `bumper` (uid/gid `1000`). In the
checked-in Compose files, `/bumper/data` is the writable state volume and
`/bumper/certs` is provided via read-only Docker configs.

A named volume takes ownership from the image and needs no manual step. The
container starts as root, repairs ownership of writable mounted paths when it
can (capabilities granted by the checked-in Compose files), and then drops to
`bumper`. If you use a custom writable host directory, ensure it is readable or
writable as needed by uid/gid `1000`.

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

!!! note "Alias"

    This uses the [`docker-swarm-compose` alias](https://github.com/MVladislav/.dotfiles/blob/main/profiles/profile5-containers#L9),
    which is maintained in the dotfiles repository. Pass the compose file with `-f`;
    setting `COMPOSE_FILE` is not enough. The final argument is the stack name.

```sh
# pulls ghcr.io/mvladislav/bumper, tag from VERSION_BUMPER (default "latest")
docker-swarm-compose deebot

# with a non-default compose file (for example the Traefik variant)
docker-swarm-compose -f docker-compose-traefik.yaml deebot

# or plain Docker Compose: builds the image from this checkout
docker compose up -d
```

**Step 4 - Access the UI**

Visit `https://ecovacs.net/` in your browser.

---

## 🗂️ Extra data files (voices, CodePush)

Voice files and CodePush packages are large and are not part of the image or
repository, so they live in the data volume: `/bumper/data/voices` and
`/bumper/data/codepush` inside the container (`BUMPER_VOICES` and
`BUMPER_CODEPUSH` override the paths). [Features](../usage/features.md) explains
what needs them.

The files either live in that volume already or are copied into it:

```sh
docker cp ./data/voices/.   <container>:/bumper/data/voices/
docker cp ./data/codepush/. <container>:/bumper/data/codepush/
```

With Swarm the named volume is local to a node, so the files have to exist on
the node that runs the task (or be copied into the volume there).

The files are downloaded by the maintainer scripts; see
[Static Data Update](../development/static-data-update.md).

---

## 🛠 Build a Custom Image

**Step 1 - Clone the repository** (if not already done)

```sh
git clone https://github.com/MVladislav/bumper.git
cd bumper
```

**Step 2 - Build**

```sh
# same name and tag the Compose file expects
docker build -t ghcr.io/mvladislav/bumper:latest .
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
  -v $PWD/certs:/bumper/certs \
  -p 443:443 -p 8007:8007 -p 1883:1883 -p 8883:8883 -p 5223:5223 \
  --name bumper \
  ghcr.io/mvladislav/bumper:latest
```

- **Volumes**: `bumper_data` holds Bumper state. Mount a writable host
  directory at `/bumper/certs` if you want generated certificates to persist
  across container recreation; you can also pre-create certificates with
  `scripts/certs/create-cert.sh`. Without a persistent writable certs mount, a
  new container may generate a new CA and clients that trusted the old CA will
  fail.
- **Ports**: 443 (HTTPS), 8007 (HTTP), 1883 (plain MQTT), 8883 (MQTT over TLS),
  5223 (XMPP over TLS)

---

_For advanced Docker parameters (resource limits, secrets, configs), see the [Environment Variables](../configuration/environment.md)._
