#!/usr/bin/env python3
"""Check a dex's string_ids table the way ART does.

ART refuses to load a dex whose `string_ids` are not sorted by string content
(`DexFile::VerifyIntegrity` -> "Out-of-order string_ids"), so a same-length
string replacement still has to land in the right sort position.

Prints each violation, or nothing when the table is sorted.

Usage: check-dex-strings.py <apk|dex> [classes.dex ...]
"""

import hashlib
import struct
import sys
import zipfile
import zlib
from pathlib import Path

MAX_REPORT = 10


def verify_dex_integrity(data: bytes) -> bool:
    """Return True when the dex header's signature and checksum match its contents.

    A dex starts with `magic[8]`, `checksum u4`, `signature[20]`, then the rest.
    The signature is the SHA-1 of bytes 32..end and the checksum the Adler-32 of
    bytes 12..end, i.e. including the signature. ART checks both.
    """
    checksum = struct.unpack_from("<I", data, 8)[0]
    return checksum == zlib.adler32(data[12:]) & 0xFFFFFFFF and data[12:32] == hashlib.sha1(data[32:]).digest()


def read_uleb128(data: bytes, pos: int) -> tuple[int, int]:
    """Read an unsigned LEB128, returning (value, next position)."""
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def mutf8_units(raw: bytes) -> tuple[int, ...]:
    """Decode MUTF-8 to the UTF-16 code units the dex format sorts by.

    MUTF-8 is not UTF-8 and raw byte order is not code point order: U+0000 is
    `C0 80`, which sorts after `01` (U+0001) as bytes. Characters above the BMP
    are CESU-8 surrogate pairs, compared as two separate UTF-16 units.
    """
    units: list[int] = []
    index = 0
    size = len(raw)
    while index < size:
        byte = raw[index]
        if byte < 0x80:  # 0xxxxxxx
            units.append(byte)
            index += 1
        elif byte & 0xE0 == 0xC0:  # 110xxxxx
            units.append(((byte & 0x1F) << 6) | (raw[index + 1] & 0x3F))
            index += 2
        elif byte & 0xF0 == 0xE0:  # 1110xxxx, includes CESU-8 surrogates
            units.append(
                ((byte & 0x0F) << 12) | ((raw[index + 1] & 0x3F) << 6) | (raw[index + 2] & 0x3F),
            )
            index += 3
        else:  # 4-byte sequences are not valid MUTF-8
            units.append(byte)
            index += 1
    return tuple(units)


def dex_strings(dex: bytes) -> list[bytes]:
    """Return the raw MUTF-8 bytes of every string, in string_ids order."""
    count, table = struct.unpack_from("<II", dex, 56)
    out = []
    for index in range(count):
        (offset,) = struct.unpack_from("<I", dex, table + 4 * index)
        _, pos = read_uleb128(dex, offset)
        end = dex.index(b"\x00", pos)
        out.append(dex[pos:end])
    return out


def show(raw: bytes) -> str:
    """Render a string for a log line without blowing up on binary content."""
    return repr(raw[:60])


def check(dex: bytes, label: str) -> int:
    """Return the number of sortedness violations found in `dex`."""
    raw_strings = dex_strings(dex)
    keys = [mutf8_units(raw) for raw in raw_strings]
    violations = 0
    for index in range(1, len(keys)):
        previous, current = keys[index - 1], keys[index]
        if previous > current:
            violations += 1
            if violations <= MAX_REPORT:
                at = next((i for i, (a, b) in enumerate(zip(previous, current)) if a != b), min(len(previous), len(current)))
                print(f"  {label}[{index - 1}] > {label}[{index}] at unit {at} (U+{current[at]:04X})")
                print(f"    {index - 1}: len={len(previous)} {show(raw_strings[index - 1])}")
                print(f"    {index:>4}: len={len(current)} {show(raw_strings[index])}")
    return violations


def main() -> int:
    target = Path(sys.argv[1])
    names = sys.argv[2:] or ["classes.dex"]
    if target.suffix == ".dex":
        blobs = {target.name: target.read_bytes()}
    else:
        with zipfile.ZipFile(target) as archive:
            blobs = {name: archive.read(name) for name in names if name in archive.namelist()}

    total = 0
    for name, blob in blobs.items():
        count = check(blob, name)
        total += count
        print(f"{name}: {'OK' if not count else f'{count} violation(s)'}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
