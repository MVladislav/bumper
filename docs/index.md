# Welcome to Bumper 🤖

Bumper is a local replacement for Ecovacs cloud services,
allowing your robots and apps to connect entirely within your home network —
without needing access to the original cloud.

It supports both XMPP and MQTT-based models transparently.

> **Disclaimer:** This project is a work in progress and may contain errors or missing parts.
> Please refer to the documentation and source code for complete details.

---

## ⚙️ Requirements

- A Wi-Fi enabled Ecovacs robot
- A server in your local network to run the Bumper services
- Python (latest version) with [uv](https://pypi.org/project/uv/) **or** Docker
- A DNS server capable of overriding specific domain queries
- A client that can connect and control the robot:
    - The official "Ecovacs" or "Ecovacs Home" Android/iOS apps (when configured correctly)
        - See [Using Bumper with the official App](usage/mobile_app.md) for mobile setup details.
    - [DeebotUniverse/client.py](https://github.com/DeebotUniverse/client.py) for command-line control

---

## 🚀 Quick Start

### 1. 🤖 Prepare your Robot

- Set up your robot using the official Ecovacs app (initial Wi-Fi configuration, registration, etc.)

### 2. 🌐 Set up DNS

- Configure your local DNS server to override specific Ecovacs domains.
- Detailed setup instructions: [DNS Setup](getting_started/dns.md)

### 3. 🛠️ Install and Run Bumper

- Follow the installation and usage instructions in the [README.md](https://github.com/MVladislav/bumper/blob/main/README.md)  
  or refer to [Docker Setup](usage/docker.md) if using Docker.

### 4. 🔒 Certificates

- Bumper requires valid certificates to operate.
- Instructions for manually creating certificates are available here: [Create Certificates](getting_started/certificates.md)

---

## 📋 Logs and Troubleshooting

Bumper writes log files into the `/logs` directory by default.  
You can also monitor real-time output:

- **If running manually**: logs appear directly in the terminal.
- **If running via Docker**: use `docker logs <container-name>` to view logs.

For more detailed output and debugging:

- Additional debugging can be enabled using environment variables.  
  See [Environment Variables](configuration/environment.md) for a list of available debug options.

---

# 📚 Next Steps

- [How Bumper Works](internals/architecture.md)

Happy cleaning! 🧹
