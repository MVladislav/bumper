#!/usr/bin/env python3
"""Inject a PEM certificate into Goat RAM over U-Boot UART (Option: simple replacement).

This automates the host-side loader in docs/internals/certificate-unpinning-goat.md.
It sends U-Boot ``mw.l``/``mw.b`` commands over serial to write the certificate
into RAM, then prints the ``ext4write`` command to run in U-Boot.

It does NOT execute ``ext4write`` (that runs in the Goat's U-Boot shell) and does
not reboot the device. Complete the Goat doc steps first: interrupt boot into
Hobot/U-Boot, select the eMMC/userdata partition, and verify the target path.

Usage:
    python3 -m venv .venv
    source .venv/bin/activate
    python3 -m pip install pyserial

    python3 scripts/device/install-goat-certs-serial.py \
        --port /dev/ttyACM0 \
        --cert ./certs/ca.crt \
        --target /certs/master.pem \
        --mmc-part 10
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError:  # pragma: no cover - runtime dependency
    serial = None  # type: ignore[assignment]


def read_pem(path: Path) -> bytes:
    """Read a PEM certificate file."""
    data = path.read_bytes()
    if b"-----BEGIN CERTIFICATE-----" not in data:
        msg = f"file does not look like a PEM certificate: {path}"
        raise ValueError(msg)
    return data


def build_memory_writes(data: bytes, address: int) -> list[str]:
    """Build U-Boot memory-write commands for raw bytes."""
    commands: list[str] = []
    i = 0
    size = len(data)
    addr = address
    while i + 4 <= size:
        word = int.from_bytes(data[i : i + 4], "little")
        commands.append(f"mw.l {addr:#010x} 0x{word:08x} 1")
        addr += 4
        i += 4
    while i < size:
        commands.append(f"mw.b {addr:#010x} 0x{data[i]:02x} 1")
        addr += 1
        i += 1
    return commands


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Inject a PEM certificate into Goat RAM over U-Boot serial and print the ext4write command. "
            "Requires an active Hobot/U-Boot session on the Goat (see docs/internals/certificate-unpinning-goat.md)."
        ),
    )
    parser.add_argument("--port", required=True, help="Serial device, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument(
        "--cert",
        type=Path,
        default=Path("./certs/ca.crt"),
        help="PEM certificate to inject (default: ./certs/ca.crt, Bumper CA)",
    )
    parser.add_argument("--target", default="/certs/master.pem", help="Target path on userdata (default: /certs/master.pem)")
    parser.add_argument(
        "--mmc-part", type=int, default=10, help="Userdata MMC partition index (default: 10 for Goat O500 mmc 0:10)"
    )
    parser.add_argument(
        "--address",
        type=lambda v: int(v, 0),
        default=0xC2600000,
        help="RAM address for injection (default: 0xC2600000)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.005,
        help="Delay between serial lines in seconds (default: 0.005; increase if U-Boot drops input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print planned actions/commands without opening the serial port",
    )
    return parser


def main() -> int:
    """Run the injector."""
    args = build_parser().parse_args()
    data = read_pem(args.cert)
    commands = build_memory_writes(data, args.address)
    size = len(data)

    print(f"Certificate: {args.cert} ({size} bytes)")
    print(f"Inject RAM:  0x{args.address:08X} via {len(commands)} U-Boot writes")
    print(f"Target:      mmc 0:{args.mmc_part}:{args.target}")
    ext4write = f"ext4write mmc 0:{args.mmc_part} 0x{args.address:08X} {args.target} 0x{size:x}"
    verify = f"md.b 0x{args.address:08X} 0x{size:x}"

    if args.dry_run:
        print(f"Verify load (U-Boot): {verify}")
        print(f"Write (U-Boot):       {ext4write}")
        print("Dry run: no serial connection opened.")
        return 0

    if serial is None:
        print("pyserial is required:", file=sys.stderr)
        print("  python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install pyserial", file=sys.stderr)
        return 1

    try:
        ser = serial.serial_for_url(
            args.port,
            args.baud,
            timeout=0.1,
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
        time.sleep(2)
        print(f"Connected to {args.port} at {args.baud} baud.")
        print("Writing... (takes time)")
        for cmd in commands:
            ser.write(cmd.encode("utf-8") + b"\n")
            ser.flush()
            time.sleep(args.delay)
    except serial.SerialException as exc:
        print(f"UART error: {exc}", file=sys.stderr)
        return 1
    finally:
        if ser.is_open:
            ser.close()
            print("UART connection closed.")

    print(f"\nTotal size (hex): 0x{size:x}")
    print(f"Verify load (U-Boot): {verify}")
    print(f"Write (U-Boot):       {ext4write}")
    print("Run the verify/write commands in the Goat U-Boot shell, then reboot (reset).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
