# Bumper

![License GPLv3](https://img.shields.io/github/license/MVladislav/bumper.svg?color=brightgreen)
[![CI Status](https://github.com/MVladislav/bumper/actions/workflows/ci.yml/badge.svg)](https://github.com/MVladislav/bumper/actions/workflows/ci.yml)
[![CodeQL](https://github.com/MVladislav/bumper/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/MVladislav/bumper/actions/workflows/codeql-analysis.yml)
[![Codecov](https://codecov.io/gh/MVladislav/bumper/graph/badge.svg?token=8N89730Z1S)](https://codecov.io/gh/MVladislav/bumper)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/MVladislav/bumper/dev.svg)](https://results.pre-commit.ci/latest/github/MVladislav/bumper/dev)
[![Release Docker](https://github.com/MVladislav/bumper/actions/workflows/docker-release.yml/badge.svg)](https://github.com/MVladislav/bumper/actions/workflows/docker-release.yml)
[![Release Drafter](https://github.com/MVladislav/bumper/actions/workflows/release-drafter.yml/badge.svg)](https://github.com/MVladislav/bumper/actions/workflows/release-drafter.yml)

> **Bumper** is a self-hosted central server for Ecovacs vacuum robots.
> It replaces the Ecovacs cloud, giving you full local control through a privacy-first,
> high-performance stack: Python + uv, Docker Swarm, and NGINX.

![Web-UI Preview](docs/images/web-ui.png)

## 🔑 Key Features

- **Self-Hosted**: Operate without Ecovacs cloud servers.
- **Privacy-First**: All data stays within your network.
- **High Performance**: Built on Python 3.13.x with [uv](https://pypi.org/project/uv/) for efficient async I/O.
- **Docker Swarm & Compose**: One-command startup with turnkey NGINX configuration.
- **Modular**: Easily extend protocols and add integrations.

> **⚠️ Warning**: Branches `main`/`dev` are under active development and may be unstable. Use at your own risk.

---

## 🚀 Quickstart

### 🔧 Prerequisites

Prepare TLS certificates and minimal environment variables before any deployment:

**TLS certificates**:

Place your certs in `certs/ca.crt`, `certs/bumper.crt`, `certs/bumper.key`, or generate them:

```sh
$./scripts/create-cert.sh
```

**Environment variables**:

Create a `.env` file with at least the following:

```env
NETWORK_MODE=overlay        # by default "bridge"

# Needs to be set when running with Docker; default is auto-detected from socket
BUMPER_ANNOUNCE_IP=192.168.0.100  # your server's public/local IP
```

Full configuration options are available in the [Wiki](https://MVladislav.github.io/bumper/infos/Env_Var/).

### ✨ Docker Swarm Deployment

**Step 1 – Clone the repository**

```sh
$git clone https://github.com/MVladislav/bumper.git
$cd bumper
```

**Step 2 – Initiate Docker in Swarm mode**

```sh
$docker swarm init
```

**Step 3 – Start services**

> alias for [docker-swarm](https://github.com/MVladislav/.dotfiles/blob/0b069b6a8435a43037789d8b5c4e1c0c65c6a142/zsh/profile-append#L146)

```sh
$docker-swarm-compose deebot      # alias for Docker Swarm Compose
# or
$docker compose up -d             # standard Docker Compose
```

**Step 4 – Open the UI**

Visit `https://ecovacs.net/` in your browser.

---

## 🛠️ Running Locally (without Docker)

**Step 1 – Clone the repo**

```sh
$git clone https://github.com/MVladislav/bumper.git
$cd bumper
```

**Step 2 – Prepare environment**

```sh
$python3 -m venv .venv
$source .venv/bin/activate
$python3 -m pip install uv
```

**Step 3 – Install dependencies**

```sh
$uv sync --no-dev
```

**Step 4 – Start Bumper**

```sh
$uv run bumper
```

---

## ❄️ Nix Development

For NixOS or Nix users, a flake-based development environment is available.

**Enter the dev shell:**

```sh
$direnv allow
# or
$nix develop --impure
```

**Available commands:**

| Command     | Description                              |
| :---------- | :--------------------------------------- |
| `build`     | Build package with Nix                   |
| `test`      | Run tests                                |
| `check`     | Run all checks (fmt, lint, typecheck)    |
| `fmt`       | Format code                              |
| `lint`      | Run linter                               |
| `typecheck` | Run type checker                         |
| `serve`     | Run bumper server                        |
| `sync`      | Reinstall dependencies                   |

**Use in other flakes** (`flake.nix`):

```nix
{
  inputs.bumper.url = "github:MVladislav/bumper";

  outputs = { nixpkgs, bumper, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      specialArgs = { inherit bumper; };
      modules = [ ./configuration.nix ];
    };
  };
}
```

**NixOS service module** (`configuration.nix`):

```nix
{ bumper, ... }:
{
  imports = [ bumper.nixosModules.bumper ];

  nixpkgs.overlays = [ bumper.overlays.default ];

  services.bumper = {
    enable = true;
    announce = "192.168.1.100";  # your server IP
    certsDir = "/path/to/certs";
    openFirewall = true;
  };
}
```

---

## 📖 Documentation

In-depth guides and architecture details are available in the `docs/` folder or online:

- **Online**: [Wiki](https://MVladislav.github.io/bumper/)
- **How It Works**: `docs/infos/How_It_Works.md`
- **Docker Usage**: `docs/configs/Docker.md`
- **Integrate with Your App**: `docs/configs/Use_With_App.md`

---

## 🔄 Compatibility

### 🤖 Supported Robots

> Note: There are several EcoVacs models that have not been tested yet.
>
> However, it has only been reported to work on the following models:

| Model              | Protocol | Version            | App Tested                                                                                                         |
| :----------------- | :------- | :----------------- | :----------------------------------------------------------------------------------------------------------------- |
| Deebot 900/901     | MQTT     |                    | Ecovacs / Ecovacs Home                                                                                             |
| Deebot 600         | MQTT     |                    | Ecovacs Home                                                                                                       |
| Deebot Ozmo 950    | MQTT     |                    | Ecovacs Home                                                                                                       |
| Deebot T10 Plus    | MQTT     | `1.7.2`            | Ecovacs Home                                                                                                       |
| Deebot T10 Plus    | MQTT     | `1.7.5`            | See [Defeating Certificate Pinning (BOT)](https://mvladislav.github.io/bumper/internals/certificate-unpinning-bot) |
| Deebot T80 Omni    | MQTT     | `1.15.0`/`1.36.0`  | See [Discussion #90](https://github.com/MVladislav/bumper/discussions/90)                                          |
| Deebot X1 Omni     | MQTT     | `1.15.7`/`2.3.9`   | See [Discussion #51](https://github.com/MVladislav/bumper/discussions/51)                                          |
| Deebot X2 Pro Omni | MQTT     | `1.76.6`/`1.81.10` | See [Discussion #56](https://github.com/MVladislav/bumper/discussions/56)                                          |
| Deebot X9 Pro Omni | MQTT     | `1.17.0`/`1.42.2`  | See [Discussion #97](https://github.com/MVladislav/bumper/discussions/97)                                          |
| Deebot Ozmo 601    | XMPP     |                    | Ecovacs                                                                                                            |
| Deebot Ozmo 930    | XMPP     |                    | Ecovacs / Ecovacs Home                                                                                             |
| Deebot M81 Pro     | XMPP     |                    | Ecovacs                                                                                                            |

### 📱 Supported Apps

| Service                        | Version    | Works | Notes                                                                                                          |
| :----------------------------- | :--------- | :---- | :------------------------------------------------------------------------------------------------------------- |
| Ecovacs Home                   | `2.2.1`    | ✅    |                                                                                                                |
| Ecovacs Home                   | `2.4.1`    | ✅    | Works best                                                                                                     |
| Ecovacs Home                   | `2.4.3`    | ✅    |                                                                                                                |
| Ecovacs Home                   | >= `2.4.4` | 🛠️    | [Defeating Certificate Pinning (APP)](https://mvladislav.github.io/bumper/internals/certificate-unpinning-app) |
| Deebot 4 Home Assistant        | `2.1.2`    | ✅    |                                                                                                                |
| EcovacsBumper (HA integration) | `1.5.3`    | ✅    |                                                                                                                |

---

## 👥 Community

Join our Gitter channel to discuss features, report issues, and share setups:

[![Gitter chat](https://badges.gitter.im/gitterHQ/gitter.png)](https://gitter.im/ecovacs-bumper/community)

Or use the GitHub Discussions section for longer conversations and proposals.

---

## 🤝 Contributing

Contributions are welcome! To get started:

1. Fork the repo and create a feature branch.
2. Run tests and linters:
   ```sh
   $uv run pytest
   $uv run mypy
   ```
3. Submit a pull request against `main`.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines.

---

## 🧪 Testing Needed

Bumper relies on community testing for broader device coverage. If you test Bumper with your robot, please open an issue with:

- Robot model and firmware
- App version
- Protocol used (MQTT/XMPP)
- Success or failure details

---

## 📜 License

Released under the [GPLv3 License](LICENSE).

---

## 🗂 References

- <https://github.com/bmartin5692/bumper>
- <https://github.com/edenhaus/bumper>
- <https://github.com/Yakifo/amqtt>
  - <https://github.com/MVladislav/amqtt>
- <https://github.com/DeebotUniverse/client.py>

---

## 🙏 Thanks

Special thanks to:

- **@torbjornaxelsson** for the original Bumper implementation.
- **@wpietri** and contributors of [Sucks](https://github.com/wpietri/sucks) for the open‑source Ecovacs client.
- All community members who test and contribute to making Bumper better.

_Originally forked from [edenhaus/bumper](https://github.com/edenhaus/bumper) (via [bmartin5692](https://github.com/bmartin5692/bumper)) · Maintained by @MVladislav_
