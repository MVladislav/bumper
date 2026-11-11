#!/usr/bin/env python3
"""Install Bumper CA/certs on an Ecovacs vacuum bot over a serial shell.

This automates the file writes in "Option 1: Simple Certificate Replacement",
step 4 of docs/internals/certificate-unpinning-bot.md. It assumes you already
completed steps 1-3: UART connected, boot interrupted, Linux shell started with
``init=/bin/bash``, and ``/data`` mounted.

The script writes PEM files via base64 over the serial console, so the bot only
needs a shell and ``base64`` (BusyBox base64 is sufficient). It does not reboot
the bot and does not change boot arguments.

Usage:
    python3 scripts/device/install-bot-certs-serial.py \
        --port /dev/ttyACM0 \
        --ca ./certs/ca.crt \
        --bumper ./certs/bumper.crt
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:  # pragma: no cover - runtime dependency
    serial = None  # type: ignore[assignment]

# Targets on the bot (Option 1, step 4).
CA_CRT = "/data/ca.crt"
CA_PEM = "/data/ca-certificates/ca.pem"
BUNDLE = "/data/ca-certificates/ca-certificates.crt"
BUNDLE_MARKER_BEGIN = "# BEGIN BUMPER CERTS"
BUNDLE_MARKER_END = "# END BUMPER CERTS"


def read_pem(path: Path, label: str) -> bytes:
    """Read a PEM file and require certificate markers."""
    data = path.read_bytes()
    if b"-----BEGIN CERTIFICATE-----" not in data:
        msg = f"{label} does not look like a PEM certificate: {path}"
        raise ValueError(msg)
    if not data.endswith(b"\n"):
        data += b"\n"
    return data


def sh_single_quote(value: str) -> str:
    """Quote a value for a POSIX shell single-quoted argument."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def send_line(ser: serial.SerialBase, line: str, delay: float) -> None:
    """Send one line and flush."""
    ser.write(line.encode("utf-8") + b"\n")
    ser.flush()
    time.sleep(delay)


def base64_decode_cmd(src: str, dst_op: str, dst: str) -> str:
    """Return a shell command that decodes base64 with BusyBox/GNU compatibility."""
    src_q = sh_single_quote(src)
    dst_q = sh_single_quote(dst)
    return (
        f"(base64 -d {src_q} 2>/dev/null || busybox base64 -d {src_q} 2>/dev/null || openssl base64 -d -in {src_q}) "
        f"{dst_op} {dst_q}"
    )


def write_file_via_base64(ser: serial.SerialBase, remote: str, content: bytes, delay: float) -> None:
    """Overwrite a remote file by streaming base64 through the shell."""
    encoded = base64.b64encode(content).decode("ascii")
    chunk_size = 512
    tmp_b64 = f"{remote}.bumper.b64"
    send_line(ser, f"rm -f {sh_single_quote(tmp_b64)}", delay)
    for i in range(0, len(encoded), chunk_size):
        chunk = encoded[i : i + chunk_size]
        send_line(ser, f"printf %s {sh_single_quote(chunk)} >> {sh_single_quote(tmp_b64)}", delay)
    send_line(ser, base64_decode_cmd(tmp_b64, ">", remote), delay)
    send_line(ser, f"rm -f {sh_single_quote(tmp_b64)}", delay)
    send_line(ser, f"echo BUMPER_WROTE:{sh_single_quote(remote)}:$?", delay)


def append_bundle_via_base64(
    ser: serial.SerialBase,
    ca_crt: bytes,
    bumper_crt: bytes,
    delay: float,
) -> None:
    """Append bumper+ca certs to the CA bundle once, with a removable marker block.

    Re-running replaces the previous BUMPER block to avoid duplicate certs.
    """
    block = BUNDLE_MARKER_BEGIN.encode() + b"\n" + bumper_crt + ca_crt + BUNDLE_MARKER_END.encode() + b"\n"
    encoded = base64.b64encode(block).decode("ascii")
    chunk_size = 512
    send_line(ser, f"rm -f {sh_single_quote(BUNDLE)}.bumper.b64 {sh_single_quote(BUNDLE)}.bumper.new", delay)
    # Remove a previous BUMPER block if present; keep the original bundle intact otherwise.
    send_line(
        ser,
        "if grep -q "
        + sh_single_quote(BUNDLE_MARKER_BEGIN)
        + " "
        + sh_single_quote(BUNDLE)
        + " 2>/dev/null; then "
        + "awk "
        + sh_single_quote(
            f"/{BUNDLE_MARKER_BEGIN}/{{skip=1;next}} /{BUNDLE_MARKER_END}/{{skip=0;next}} !skip{{print}}",
        )
        + " "
        + sh_single_quote(BUNDLE)
        + " > "
        + sh_single_quote(BUNDLE + ".bumper.new")
        + " && mv "
        + sh_single_quote(BUNDLE + ".bumper.new")
        + " "
        + sh_single_quote(BUNDLE)
        + "; fi",
        delay,
    )
    for i in range(0, len(encoded), chunk_size):
        chunk = encoded[i : i + chunk_size]
        send_line(ser, f"printf %s {sh_single_quote(chunk)} >> {sh_single_quote(BUNDLE)}.bumper.b64", delay)
    send_line(ser, base64_decode_cmd(BUNDLE + ".bumper.b64", ">>", BUNDLE), delay)
    send_line(ser, f"rm -f {sh_single_quote(BUNDLE)}.bumper.b64", delay)
    send_line(ser, f"echo BUMPER_APPENDED:{sh_single_quote(BUNDLE)}:$?", delay)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Write Bumper certificates to an Ecovacs vacuum bot over serial. "
            "Requires an active shell on the bot with /data mounted (see "
            "docs/internals/certificate-unpinning-bot.md, Option 1 steps 1-3)."
        ),
    )
    parser.add_argument("--port", required=True, help="Serial device, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--ca", type=Path, default=Path("./certs/ca.crt"), help="Path to CA PEM (default: ./certs/ca.crt)")
    parser.add_argument(
        "--bumper",
        type=Path,
        default=Path("./certs/bumper.crt"),
        help="Path to Bumper server PEM (default: ./certs/bumper.crt)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.01,
        help="Delay between serial lines in seconds (default: 0.01; increase if the shell drops input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print planned actions without opening the serial port",
    )
    return parser


def main() -> int:
    """Run the installer."""
    args = build_parser().parse_args()
    ca_crt = read_pem(args.ca, "CA certificate")
    bumper_crt = read_pem(args.bumper, "Bumper certificate")

    planned = [
        f"overwrite {CA_CRT} with {args.ca}",
        f"overwrite {CA_PEM} with {args.ca}",
        f"append BUMPER cert block (bumper.crt, then ca.crt) to {BUNDLE}",
    ]
    print("Planned actions (requires bot shell with /data mounted):")
    for item in planned:
        print(f"  - {item}")

    if args.dry_run:
        print("Dry run: no serial connection opened.")
        return 0

    if serial is None:
        print("pyserial is required: pip install pyserial", file=sys.stderr)
        return 1

    try:
        ser = serial.serial_for_url(
            args.port,
            args.baud,
            timeout=0.2,
            bytesize=8,
            parity="N",
            stopbits=1,
            rtscts=False,
            xonxoff=False,
            do_not_open=True,
        )
        ser.dtr = None
        ser.rts = None
        ser.exclusive = False
        ser.open()
    except serial.SerialException as exc:
        print(f"UART error: {exc}", file=sys.stderr)
        return 1

    try:
        time.sleep(1)
        print(f"Connected to {args.port} at {args.baud} baud.")
        print("Writing certificates (this can take a moment over UART)...")
        write_file_via_base64(ser, CA_CRT, ca_crt, args.delay)
        write_file_via_base64(ser, CA_PEM, ca_crt, args.delay)
        append_bundle_via_base64(ser, ca_crt, bumper_crt, args.delay)
        send_line(ser, "sync", args.delay)
        send_line(
            ser,
            f"echo BUMPER_DONE; ls -l {sh_single_quote(CA_CRT)} {sh_single_quote(CA_PEM)} {sh_single_quote(BUNDLE)}",
            args.delay,
        )
        time.sleep(0.5)
    except serial.SerialException as exc:
        print(f"UART error: {exc}", file=sys.stderr)
        return 1
    finally:
        if ser.is_open:
            ser.close()
            print("UART connection closed.")

    print("Commands sent. Verify on the bot (check BUMPER_WROTE/BUMPER_APPENDED/BUMPER_DONE output), then reboot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
