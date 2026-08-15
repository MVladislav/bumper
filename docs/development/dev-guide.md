# Development Guide

This guide covers setting up a local development environment, running the application, and maintaining code quality.

---

## 🔧 Prerequisites

- Python 3.13.x installed
- Git

---

## 🛠️ Setup Local Environment

**Step 1 – Clone the repository**

```sh
$git clone https://github.com/MVladislav/bumper.git
$cd bumper
```

**Step 2 – Create and activate virtual environment, install uv**

```sh
$python3 -m venv .venv
$source .venv/bin/activate
$python3 -m pip install uv
```

**Step 3 – Install project dependencies**

```sh
$uv sync --all-groups --upgrade
```

---

## 🚀 Running the Application

```sh
$./scripts/create-cert.sh
$WEB_SERVER_HTTPS_PORT=8443 uv run bumper
```

The web UI will be available at `https://127.0.1.1:8443` by default.

---

## ✅ Code Quality and Testing

### Linting & Static Analysis

**Run prek hooks**

```sh
$prek run --all-files
```

**Type checking with mypy**

```sh
$uv run --frozen mypy bumper/
```

**Linting with pylint**

```sh
$uv run --frozen pylint bumper/
```

### Unit Tests

**Run tests**

```sh
$uv run pytest tests
```

**Tests with coverage report**

```sh
$uv run pytest --cov=./ tests --cov-report xml --junitxml=pytest-report.xml
```

**Generate HTML coverage report**

```sh
$uv run pytest --cov=./ tests --cov-report html:tests/report
```

The HTML report is located at `tests/report/index.html`.

---

## 📖 Understanding the Code

Refer to the [How It Works](../internals/architecture.md) guide for an overview of the core architecture and data flows.

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

See [CONTRIBUTING.md](https://github.com/MVladislav/bumper/blob/main/CONTRIBUTING.md) for detailed contribution guidelines.
