# Command-Line Usage

**Bumper** supports several command-line arguments, which you can view by using the `-h` flag.

> **Note:** For more detailed configuration, use environment variables. See [Environment Variables](../configuration/environment.md).

```sh
usage: bumper [-h] [--listen LISTEN] [--announce ANNOUNCE] [--debug_level DEBUG_LEVEL] [--debug_verbose DEBUG_VERBOSE]

options:
  -h, --help                    Show this help message and exit
  --listen LISTEN               Start serving on address (default: from socket)
  --announce ANNOUNCE           Announce address to bots on check-in (default: from --listen)
  --debug_level DEBUG_LEVEL     Set debug log level (default: "INFO")
  --debug_verbose DEBUG_VERBOSE Enable verbose debug logs (default: 1)
```

---

## ⚠️ Linux: Binding Port 443 Without Root (non-Docker)

Bumper's HTTPS web server binds to port **443** by default. On Linux, ports below 1024
require either root privileges or the `CAP_NET_BIND_SERVICE` capability.

When running Bumper directly (not via Docker, which handles this through port mapping),
you must grant that capability to the Python binary used by uv:

```bash
sudo setcap cap_net_bind_service=+ep \
  $(readlink -f $(which python3))
```

Or, if you installed Python via uv:

```bash
sudo setcap cap_net_bind_service=+ep \
  ~/.local/share/uv/python/cpython-3.13.*/linux-x86_64-gnu/bin/python3.13
```

> **Note:** This must be re-applied if uv installs a new Python patch release
> (e.g. `3.13.12` → `3.13.13`), since the binary path changes.

**Alternative:** Change the HTTPS port to something above 1024 via the
`WEB_SERVER_HTTPS_PORT` environment variable (see
[Environment Variables](../configuration/environment.md)):

```bash
WEB_SERVER_HTTPS_PORT=8443 uv run bumper --listen <YOUR_IP>
```
