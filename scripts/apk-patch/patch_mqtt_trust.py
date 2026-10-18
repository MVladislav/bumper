#!/usr/bin/env python3
"""Stop the Ecovacs app from pinning a certificate for MQTT.

The app's Paho fork builds its MQTT ``SSLSocketFactory`` from a certificate
embedded in a ``classes*.dex`` and loads it into an empty ``KeyStore``::

    // p000/ceb.m708v()  (TechCloud, "renamed from: v")
    ks.load(null);
    ks.setCertificateEntry("aliasInTechCloud",
        CertificateFactory.getInstance("X.509")
            .generateCertificate(new ByteArrayInputStream(Base64.decode(PIN, 0))));
    tmf.init(ks);                    // <-- app-supplied KeyStore, replaces the platform store

``TrustManagerFactory.init(ks)`` with a non-null KeyStore overrides the platform
trust store, so ``network_security_config.xml`` never applies and the handshake
fails with ``CertPathValidatorException: Trust anchor for certification path not
found``.

This patches the *string*, not the certificate. ``generateCertificate`` throwing
is enough: ``m708v`` catches ``Exception`` and returns ``null``, and Paho's
``SSLNetworkModuleFactory`` treats a null socket factory as "no SSL properties
supplied" and builds the context with null trust managers, i.e. the platform
store::

    if (sf == null) { sf = new SSLSocketFactoryFactory().createSocketFactory(null); }

So the replacement keeps a prefix of the original string and fills the rest with
a marker. ``Base64.decode(str, 0)`` skips every character outside the Base64
alphabet, so what remains cannot decode to a certificate.

The prefix matters because ART verifies that the dex ``string_ids`` table is
sorted by UTF-16 code point and rejects the file otherwise::

    Out-of-order string_ids: 'LS0t...' then 'LS0t...'

Same-length replacement is therefore not enough - it moves the string within the
sort order. Holding a prefix keeps its position. The result is re-checked with
``check_dex_strings.py`` and the patch is refused if the table is out of order.

Usage:
    patch_mqtt_trust.py SRC.apk DST.apk [--force]
"""

import argparse
import base64
import hashlib
import struct
import sys
import zipfile
import zlib
from pathlib import Path

from apk_io import repack as repack_apk
from check_dex_strings import dex_strings, mutf8_units, verify_dex_integrity

FILLER = " bumper-patch: mqtt trust now comes from the Android platform store "


class PatchError(Exception):
    """Raised when the pin cannot be located or the replacement will not sort."""


def refresh_dex_header(dex: bytearray) -> None:
    """Recompute the dex header's SHA-1 signature and Adler-32 checksum in place.

    A dex starts with `magic[8]`, `checksum u4`, `signature[20]`, then the rest of
    the file. The signature is the SHA-1 of bytes 32..end and the checksum is the
    Adler-32 of bytes 12..end, i.e. including the signature, so the signature is
    written first.
    """
    dex[12:32] = hashlib.sha1(bytes(dex[32:])).digest()
    dex[8:12] = struct.pack("<I", zlib.adler32(bytes(dex[12:])) & 0xFFFFFFFF)


def build_replacement(pin: str, previous: str | None, following: str | None) -> str:
    """Return a same-length replacement for `pin` that keeps its sort position.

    ART requires `previous <= replacement <= following` in UTF-16 code point
    order. The neighbours are other Base64 PEM blobs and `pin` is a prefix of the
    string above it, so holding a prefix of `pin` satisfies both bounds. Grow the
    prefix until they hold; the shortest prefix that works also leaves the fewest
    decodable bytes behind.
    """
    floor = mutf8_units(previous.encode()) if previous is not None else None
    ceiling = mutf8_units(following.encode()) if following is not None else None
    pin_units = mutf8_units(pin.encode())
    for keep in range(1, len(pin)):
        head = pin[:keep]
        candidate = (head + FILLER)[: len(pin)].ljust(len(pin), " ")
        if len(mutf8_units(candidate.encode())) != len(pin_units):
            continue
        units = mutf8_units(candidate.encode())
        if floor is not None and units < floor:
            continue
        if ceiling is not None and units > ceiling:
            continue
        return candidate
    msg = (
        "no replacement of the same length keeps string_ids sorted, so patching "
        "this literal in place would leave an unloadable dex. Re-check with "
        "check_dex_strings.py."
    )
    raise PatchError(msg)


PEM_HEADER = b"LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t"
BASE64_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="  # pragma: allowlist secret


def is_pinned_certificate(raw: bytes) -> bool:
    """Return True when `raw` is a Base64 PEM certificate literal.

    The app embeds several certificates (a truncated copy, a QA CA); only the
    full-length PEM blobs are the pins.
    """
    kept = bytes(c for c in raw if c in BASE64_ALPHABET)
    if len(kept) < 200:
        return False
    padded = kept + b"=" * (-len(kept) % 4)
    try:
        decoded = base64.b64decode(padded)
    except ValueError:
        return False
    return decoded.startswith(b"-----BEGIN CERTIFICATE-----")


def patch_dex(data: bytes) -> tuple[bytes, list[str], list[str]]:
    """Return (patched dex, replacements, pinned strings) for one dex."""
    strings = dex_strings(data)
    patches: list[tuple[bytes, str]] = []

    for index, raw in enumerate(strings):
        if PEM_HEADER not in raw or not is_pinned_certificate(raw):
            continue
        pin = raw.decode("utf-8", "replace")
        previous = strings[index - 1].decode("utf-8", "replace") if index > 0 else None
        following = strings[index + 1].decode("utf-8", "replace") if index + 1 < len(strings) else None
        patches.append((build_replacement(pin, previous, following).encode(), pin))

    if not patches:
        msg = "no hardcoded MQTT certificate found in this dex"
        raise PatchError(msg)

    patched = bytearray(data)
    replacements, pins = [], []
    for replacement, pin in patches:
        patched = bytearray(bytes(patched).replace(pin.encode(), replacement))
        replacements.append(replacement.decode("ascii", "replace"))
        pins.append(pin)
    if len(patched) != len(data):
        msg = "dex size changed, refusing to write"
        raise PatchError(msg)
    refresh_dex_header(patched)
    return bytes(patched), replacements, pins


def patch_apk(src: Path, dst: Path, patches: dict[str, bytes]) -> None:
    """Copy `src` to `dst`, swapping in the patched dex entries."""
    repack_apk(src, dst, patches)


def verify(dst: Path, pins: list[str], replacements: list[str]) -> bool:
    """Confirm every pin is gone and every dex still has a sorted string table."""
    with zipfile.ZipFile(dst) as archive:
        blobs = {name: archive.read(name) for name in archive.namelist() if name.endswith(".dex")}
    for name, blob in blobs.items():
        if any(pin.encode() in blob for pin in pins):
            return False
        if not verify_dex_integrity(blob):
            return False
        keys = [mutf8_units(raw) for raw in dex_strings(blob)]
        if any(previous > current for previous, current in zip(keys, keys[1:])):
            msg = f"{name}: string_ids are no longer sorted, refusing to report success"
            raise PatchError(msg)
    return any(replacement.rstrip().encode() in blob for blob in blobs.values() for replacement in replacements)


def main(argv: list[str] | None = None) -> int:
    """Patch the app's MQTT trust store so it uses the platform trust store."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("src", type=Path, help="input APK")
    parser.add_argument("dst", type=Path, help="output APK")
    parser.add_argument("--force", action="store_true", help="overwrite an existing output file")
    args = parser.parse_args(argv)

    if args.dst.exists():
        if not args.force:
            print(f"error: {args.dst} exists (use --force)", file=sys.stderr)
            return 1
        args.dst.unlink()

    patches: dict[str, bytes] = {}
    replacements: list[str] = []
    pins: list[str] = []
    try:
        with zipfile.ZipFile(args.src) as archive:
            for info in archive.infolist():
                if not info.filename.endswith(".dex"):
                    continue
                data = archive.read(info)
                try:
                    patched, found, removed = patch_dex(data)
                except PatchError:
                    continue
                patches[info.filename] = patched
                replacements.extend(found)
                pins.extend(removed)
                print(f"patched {len(removed)} MQTT certificate pin(s) in {info.filename}")

        if not patches:
            msg = (
                "no hardcoded MQTT certificate found in any classes*.dex. Ecovacs "
                "has changed it; this tool only neutralises a Base64 PEM literal "
                "that keeps its sorted position in string_ids."
            )
            raise PatchError(msg)
        patch_apk(args.src, args.dst, patches)
    except (PatchError, OSError, zipfile.BadZipFile, IndexError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"patched {args.src.name} -> {args.dst}")
    try:
        ok = verify(args.dst, pins, replacements)
    except PatchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not ok:
        print("error: post-patch verification failed", file=sys.stderr)
        return 1
    print(f"verified: {len(pins)} pin(s) neutralised, string_ids still sorted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
