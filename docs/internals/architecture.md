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

The official Ecovacs cloud authenticates users and binds robots to accounts, enabling control via the app. Bumper implements this flow locally:

1. **Discovery Endpoint**
    - Robot issues HTTPS GET to `lbo.ecovacs.net:8007` for service addresses.
    - App uses the same endpoint for initial configuration.
2. **Login API**
    - App encrypts credentials with Ecovacs’s public key and POSTs to `/api/login`.
    - Bumper accepts payloads and returns a session token (JWT).
3. **Session Management**
    - The token is sent in cookies or headers on subsequent REST calls.
    - Robots have no built‑in auth: once on Wi‑Fi, they connect using the stored announce IP without re‑authenticating.

> **Note:** True E2E encryption isn’t possible without Ecovacs’s private key. Bumper fakes this step to maintain compatibility.

---

## 🔒 Login / Authentication / REST API

Bumper’s Web Server module simulates the Ecovacs cloud’s REST API for login and command routing:

- **Discovery**: Robots and the mobile app retrieve service endpoints (XMPP broker or MQTT server addresses) via HTTPS requests to the discovery URL exposed on ports 443/8007.
- **Authentication**: The app submits encrypted credentials; Bumper accepts the payload and establishes a session internally, returning a token or cookie to authorize subsequent calls.
- **Command Routing**: When the app issues a command (e.g., start cleaning), it makes a REST call against Bumper’s web service. The request is enqueued and handed off to the MQTT helper or forwarded to the XMPP server, depending on the robot’s protocol.
- **Status Queries**: The app can poll for the robot’s latest state via REST endpoints, which query the latest telemetry stored by Bumper.

These paths mirror the patterns used by the official servers, ensuring the app functions unmodified.

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
    - Helper Bot captures responses and makes them available via REST for the app.

---

## ⚙️ Helper Bot

- An internal MQTT client that bridges REST API calls to MQTT topics.
- Authenticates with the same JWT and listens on command topics.
- Correlates request/response pairs by message ID for REST replies.

---

_For further details, see the source modules in [`bumper/web/server.py`](https://github.com/MVladislav/bumper/blob/main/bumper/web/server.py), [`bumper/xmpp/xmpp.py`](https://github.com/MVladislav/bumper/blob/main/bumper/xmpp/xmpp.py), and [`bumper/mqtt/server.py`](https://github.com/MVladislav/bumper/blob/main/bumper/mqtt/server.py)._
