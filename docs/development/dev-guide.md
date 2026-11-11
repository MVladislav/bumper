# Development Guide

This guide covers setting up a local development environment, running the application, and maintaining code quality.

---

## 🔧 Prerequisites

- [uv](https://docs.astral.sh/uv/) (the repository commits `uv.lock`)
- Python 3.15 recommended (3.13 and 3.14 are supported)
- Git

`uv` can install the interpreter itself, so a system Python 3.15 is optional.

---

## 🛠️ Setup Local Environment

**Step 1 - Clone the repository**

```sh
git clone https://github.com/MVladislav/bumper.git
cd bumper
```

**Step 2 - Create the virtual environment**

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install uv
```

Installing `uv` inside `.venv` keeps it out of your system Python.

**Step 3 - Install every dependency group**

```sh
uv sync --active --all-groups
```

`--all-groups` includes the development and docs tools. Activate `.venv` once
per shell; the rest of this guide uses `uv run --active`.

---

## 🚀 Running the Application (local development)

For normal deployments, use [Docker](../usage/docker.md) behind a reverse proxy (nginx or Traefik).
Running Bumper directly without the expected network/proxy setup is useful for development and debugging,
but it is not the supported user deployment path.

```sh
bash scripts/certs/create-cert.sh
WEB_SERVER_HTTPS_PORT=8443 uv run --active bumper
```

The web UI is served at `https://<BUMPER_LISTEN>:8443`. `BUMPER_LISTEN`
defaults to the address the hostname resolves to; set it explicitly (for
example `BUMPER_LISTEN=127.0.0.1`) if the default is not the address you want.

Use `uv run --active bumper --help` to list CLI options.
In containerized deployments, prefer [Environment Variables](../configuration/environment.md).

---

## 📚 Documentation

Docs are Zensical pages. Two previews, pick one:

| Preview   | Serves                             | Version selector |
| --------- | ---------------------------------- | ---------------- |
| Live      | `docs/` from disk                  | no               |
| Versioned | local `gh-pages` (`latest` + tags) | yes              |

The live preview is for checking an edit. The versioned preview is for the
selector and for a tag's own content; it is not needed to change code.

### Host

```sh
uv run --active zensical serve --dev-addr 0.0.0.0:8000
```

Open `http://<host>:8000/bumper/`.

Versioned, from the same checkout:

```sh
uv run --active mike deploy --ignore-remote-status latest
uv run --active mike set-default --ignore-remote-status latest
uv run --active mike serve --ignore-remote-status --dev-addr 0.0.0.0:8001
```

Open `http://<host>:8001/`. mike only redirects the site root, so a deep link
must name the version (`/latest/getting_started/dns/`). Add a tag from a
worktree, so the tag's own `docs/` and `mkdocs.yml` are used:

```sh
MAIN="$PWD"
git worktree add --detach /tmp/bumper-release v0.4.1
cd /tmp/bumper-release
cp "$MAIN/mkdocs.release.yml" .
uv run --project "$MAIN" --frozen --no-sync mike deploy \
  --ignore-remote-status --config-file mkdocs.release.yml v0.4.1
cd "$MAIN"
git worktree remove --force /tmp/bumper-release
```

`mkdocs.release.yml` adds the mike version provider to a tag that predates it.
Without it that tag has no version selector, so `v0.4.1` has no way back to
`latest`.

### Docker

Both are standalone. The `zensical` service only serves `docs/`; the `mike`
service serves the versioned site.

```sh
docker compose -f docker-compose-zensical.yaml up -d zensical   # :8000
docker compose -f docker-compose-zensical.yaml up -d mike       # :8001
MIKE_RELEASE_TAG=v0.4.1 docker compose -f docker-compose-zensical.yaml up -d mike
```

Swarm uses the same file through the
[`docker-swarm-compose` alias](https://github.com/MVladislav/.dotfiles/blob/main/profiles/profile5-containers#L9):

```sh
docker-swarm-compose -f docker-compose-zensical.yaml bumper-docs
MIKE_RELEASE_TAG=v0.4.1 docker-swarm-compose -f docker-compose-zensical.yaml bumper-docs
docker stack rm bumper-docs
```

The `mike` service mounts `${ZENSICAL_MAIN_PATH:-$PWD}` read-only and builds in
`/tmp/work` inside the container, so the host checkout and its `gh-pages` branch
are never modified. It rebuilds `latest` from the current docs, keeps watching
the source and redeploys `latest` when docs change, reuses the other versions
already on `gh-pages`, and adds the newest `v*` tag (or `MIKE_RELEASE_TAG`) so
the selector can switch between them. The toolchain is cached in the `docs_venv`
volume.

Remove a version with `uv run --active mike delete --ignore-remote-status <version>`.

!!! note "GitHub Pages source"

    CI publishes to `gh-pages`. In **Settings → Pages**, use
    **Deploy from a branch**, branch `gh-pages`, folder `/` (root).

---

## ✅ Code Quality and Testing

### Linting & Static Analysis

**Run prek hooks**

```sh
uv run --active prek run --all-files
```

The `no-commit-to-branch` hook rejects commits on `main`. Run the hooks from a
feature branch, or skip that one hook when checking the rest:

```sh
SKIP=no-commit-to-branch uv run --active prek run --all-files
```

**Type checking with mypy**

```sh
uv run --active --frozen mypy bumper/
```

**Linting with pylint**

```sh
uv run --active --frozen pylint bumper/
```

### Unit Tests

**Run tests**

```sh
uv run --active pytest tests
```

**Tests with coverage report**

```sh
uv run --active pytest --cov=./ tests --cov-report xml --junitxml=pytest-report.xml
```

**Generate HTML coverage report**

```sh
uv run --active pytest --cov=./ tests --cov-report html:tests/report
```

The HTML report is located at `tests/report/index.html`.

---

## 📖 Understanding the Code

Refer to the [How It Works](../internals/architecture.md) guide for an overview of the core architecture and data flows.

For route registration, response envelopes, and choosing a template for a new
endpoint, see [Web API Endpoints](web-api-endpoints.md).

---

## 🔄 Updating Static Ecovacs Data

Bumper ships with pre-fetched Ecovacs data under `bumper/web/static_api/`.
See [Static Data Update Guide](static-data-update.md).

---

## 🤝 Contributing Changes

1. Fork the repo and create a feature branch.
2. Follow the setup and testing steps above.
3. Commit changes with clear messages and update tests.
4. Open a pull request against `main`, ensuring all checks pass.

See the repository README and this development guide for contribution expectations.
Pull requests should target `main`, follow Conventional Commits, and pass
lint/type/test checks before review.
