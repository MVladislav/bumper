# Bumper 🤖

Bumper is a self-hosted replacement for Ecovacs cloud services.
It lets supported Ecovacs robots and apps talk to a server on your local network,
instead of the Ecovacs cloud.

Bumper emulates the web, MQTT, and XMPP services that the official app and robots use.
Protocol fidelity matters: the app and robots are unmodified clients,
so Bumper aims to match the behavior they expect.

!!! warning "Disclaimer"

    This project is a work in progress.
    Behavior varies by robot model, firmware, app version, and region.
    Check the documentation, [Model Compatibility](reference/models.md), and logs when troubleshooting.

---

## 🧩 How it fits together

For Bumper to work, app/robot traffic for Ecovacs domains must reach Bumper,
and the client must trust the TLS certificate Bumper presents.

```text
Official app / robot
        |
        | DNS resolves Ecovacs domains to your Bumper server
        v
   Bumper (web + MQTT + XMPP)
```

Bumper's web UI shows server status, connected sessions, registered bots/clients, and clean logs.

---

## 🚀 Getting started

Start with the step-by-step guide:

- **[Getting Started Overview](getting_started/index.md)** - the full setup path, in order.

In short:

1. [Configure DNS](getting_started/dns.md) so Ecovacs domains resolve to Bumper.
2. [Create or provide certificates](getting_started/certificates.md) on the host if you use the checked-in Compose files.
3. [Deploy Bumper](usage/docker.md) (Docker/Compose is recommended, usually behind nginx or Traefik).
4. [Connect the official app](usage/mobile_app.md) and make it trust Bumper's CA.
5. [Use robot Wi-Fi setup](getting_started/robot-onboarding.md) only when you need the app's onboarding flow.

---

## 👀 What to expect

- **`ecovacs.net` shows only helperbot:** normal when no robot or app client is connected.
  Robots appear after they connect to Bumper's services with working DNS, reachability/proxy routing,
  and certificate trust. See [Getting Started troubleshooting](getting_started/index.md#troubleshooting)
  and [What to expect](getting_started/index.md#what-to-expect).
- **Model support is empirical:** check [Model Compatibility](reference/models.md).
  Some models need certificate/key changes or have known limitations.
- **Cloud-only features may be missing:** Bumper focuses on local control and the APIs needed for that.

If you are stuck, use [Discussions](https://github.com/MVladislav/bumper/discussions) and debug logs
(`DEBUG_BUMPER_LEVEL=DEBUG`).

---

## 📚 Documentation

| Section                                       | Purpose                                                         |
| --------------------------------------------- | --------------------------------------------------------------- |
| [Getting Started](getting_started/index.md)   | DNS, certificates, deployment, app connection, robot onboarding |
| [Features](usage/features.md)                 | Voice languages, work logs/maps, app updates (CodePush)         |
| [Configuration](configuration/environment.md) | Environment variables                                           |
| [Reference](reference/models.md)              | Model reports, error codes                                      |
| [Internals](internals/architecture.md)        | Architecture, auth, sniffing, certificate unpinning             |
| [Development](development/dev-guide.md)       | Local development, API docs, static data, CI                    |
