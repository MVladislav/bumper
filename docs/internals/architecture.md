# How It Works

> **⚠️ Disclaimer:** This document is a work in progress and may contain inaccuracies or incomplete sections.
> Some parts serve as placeholders and require further refinement.
> Please refer to the source code for authoritative information, and feel free to submit corrections or improvements.

Bumper recreates Ecovacs’s central cloud services locally, so your robots and app work seamlessly within your network. It supports both **XMPP** and **MQTT** protocols.

![Bumper Diagram](../images/BumperDiagram.png "Bumper Diagram")

---

## 🧩 Services

| Service     | Description                                                | Ports      | Module Path          |
| ----------- | ---------------------------------------------------------- | ---------- | -------------------- |
| Web Server  | Handles discovery, login, REST API for commands and status | 443, 8007  | `bumper.web.server`  |
| XMPP Server | Relays XML stanzas between client and robot over XMPP      | 5223       | `bumper.xmpp.xmpp`   |
| MQTT Broker | Manages MQTT topics for telemetry and commands             | 1883, 8883 | `bumper.mqtt.server` |

---

## 🔒 App / Authentication

Bumper recreates the account and token plumbing the app expects, but it does not verify Ecovacs request signatures. The app logs in with an account name, receives an opaque access token, exchanges an IoT token for an auth code, and then receives OAuth tokens. The same auth code links the account to the XMPP or MQTT transport.

The account key is separate from the TLS key. The private half stays in the data directory, so Bumper can read the fields the app encrypts and no other server can.

One account has three public ids: `A` for the account, `U` for the unified
identity, and `I` for the IoT session. Each app installation has a client id
and resource (`K`/`R`), with its own token row. A `BumperUser` owns its app
devices, while every local account receives the shared robot inventory; legacy
ids are aliases on that same record. This keeps parallel app clients separate
without creating duplicate accounts.

See [Authentication](authentication.md) for the full flow, the trust model, and the known gaps.

---

## 🔒 Login / Authentication / REST API

Bumper’s Web Server module simulates the Ecovacs REST API for login and command routing:

- **Discovery**: Robots and the mobile app retrieve service endpoints (XMPP broker or MQTT server addresses) via HTTPS requests to the discovery URL exposed on ports 443/8007.
- **Authentication**: The app submits account data; a normal login creates or finds the local account and returns an access token, while a session check resolves the existing account by the app device. Later calls name the account with that token or with a user id. The HTTP layer does not verify request signatures.
- **Command Routing**: When the app issues a command (for example, start cleaning), it makes a REST call against Bumper’s web service. The request is enqueued and handed off to the MQTT helper or forwarded to the XMPP server, depending on the robot’s protocol.
- **Status Queries**: The app can poll for the robot’s latest state via REST endpoints, which query the latest telemetry stored by Bumper.

These paths mirror the patterns the app expects, so the app works unmodified.

## 🔗 XMPP Protocol

_Example Models: Ozmo 601, Ozmo 930_

1. **Discovery**
    - Robot and app request XMPP server info from `/discover`.
    - Bumper returns its own hostname/IP for XMPP.
2. **Connection**
    - Both robot and app open TLS on port `5223` to Bumper’s XMPP Server.
3. **Message Relay**
    - Bumper maintains separate sessions for each side and forwards XML stanzas.
    - Commands (e.g., start/stop) and status (e.g., battery) are exchanged as XMPP messages.
4. **Keep‑Alive**
    - Bumper responds to XMPP pings and sends heartbeats to prevent timeouts.

> **Tip:** The Ecovacs app attempts XMPP first; if no valid messages, it falls back to MQTT models.

---

## ☁️ MQTT Protocol

_Example Models: Deebot 600, 900, 901, Ozmo 950_

1. **Broker Connection**
    - Robot connects to Bumper’s MQTT Broker on `8883` (TLS) or `1883` (plain).
    - Subscribes to `p2p/<device_id>` for incoming commands.
2. **Telemetry Publishing**
    - Robot publishes JSON status (battery, location) to `attr/<device_id>` at intervals.
3. **Command Delivery**
    - App issues `POST /api/command` to Web Server.
    - Web Server forwards the command to the Helper Bot.
    - Helper Bot publishes the command to `p2p/<device_id>`.
4. **Response Handling**
    - Robot executes the command and publishes results back to `p2p/<device_id>` or `rsp/<device_id>`.
    - Helper Bot stores responses and makes them available via REST for the app.

---

## ⚙️ Helper Bot

- An internal MQTT client that bridges REST API calls to MQTT topics.
- Connects with a fixed client id that the broker accepts before any other check.
- Correlates request/response pairs by message ID for REST replies.

---

_For further details, see the source modules in [`bumper/web/server.py`](https://github.com/MVladislav/bumper/blob/main/bumper/web/server.py), [`bumper/xmpp/xmpp.py`](https://github.com/MVladislav/bumper/blob/main/bumper/xmpp/xmpp.py), and [`bumper/mqtt/server.py`](https://github.com/MVladislav/bumper/blob/main/bumper/mqtt/server.py)._
