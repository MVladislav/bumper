#!/usr/bin/env python3
"""Regression tests for the dex string-table invariants the MQTT patch depends on.

Both tests here exist because the first version of `patch_mqtt_trust.py`
produced an APK that would not start:

    Zip open failed: Failure to verify dex file '.../classes8.dex':
    Out-of-order string_ids: 'LS0t...' then 'LS0t...'

Keeping a replacement string the *same length* as the original is not enough -
ART also requires `string_ids` to stay sorted by UTF-16 code point. And a
byte-wise sort check is not enough either, because MUTF-8 encodes U+0000 as
`C0 80`, so raw byte order disagrees with code point order.

Run: test_patch_mqtt_trust.py
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_dex_strings import mutf8_units  # noqa: E402
from patch_mqtt_trust import (  # noqa: E402
    BASE64_ALPHABET,
    PatchError,
    build_replacement,
    is_pinned_certificate,
)

# A stand-in for the real neighbourhood in classes8.dex: the string above the
# pinned certificate is a 136-character *prefix* of it, and the one below is
# "LSS". The pin itself is the full 1720-character Base64 PEM literal.
PIN_HEAD = "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURpakNDQW5JQ0NRRGJU"
PIN = PIN_HEAD + "Q" * (1720 - len(PIN_HEAD))
PREVIOUS = PIN[:136]
FOLLOWING = "LSS"

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    """Record a test result."""
    print(f"[{'ok' if condition else 'FAIL'}] {label}{'' if condition else f' :: {detail}'}")
    if not condition:
        failures.append(label)


def test_mutf8_order() -> None:
    """U+0000 must sort before U+0001, even though C0 80 sorts after 01."""
    nul = mutf8_units(b"\xc0\x80")
    one = mutf8_units(b"\x01")
    check("mutf8: U+0000 < U+0001", nul < one, f"{nul} vs {one}")
    check("mutf8: U+0000 decodes to one unit", nul == (0,), f"{nul}")
    check("mutf8: three-byte BMP", mutf8_units("ä".encode()) == (0xE4,), "not U+00E4")
    surrogate = mutf8_units(b"\xed\xa0\xbd\xed\xb8\x80")
    check("mutf8: surrogate pair is two units", surrogate == (0xD83D, 0xDE00), f"{surrogate}")


def test_replacement_stays_sorted() -> None:
    """The replacement must fit between its neighbours and keep the length."""
    pin = PIN
    candidate = build_replacement(pin, PREVIOUS, FOLLOWING)
    check("replacement: same length", len(candidate) == len(pin), f"{len(candidate)} vs {len(pin)}")
    check(
        "replacement: >= predecessor",
        mutf8_units(candidate.encode()) >= mutf8_units(PREVIOUS.encode()),
        candidate[:60],
    )
    check(
        "replacement: <= successor",
        mutf8_units(candidate.encode()) <= mutf8_units(FOLLOWING.encode()),
        candidate[:60],
    )
    check("replacement: pin is gone", pin not in candidate, "still contains the original")
    check("replacement: marker is visible", "bumper-patch" in candidate, "marker missing")


def test_replacement_decodes_to_nonsense() -> None:
    """What android.util.Base64.decode keeps must not be a certificate."""
    pin = PIN
    candidate = build_replacement(pin, PREVIOUS, FOLLOWING)
    kept = bytes(c for c in candidate.encode() if c in BASE64_ALPHABET)
    raw = base64.b64decode(kept + b"=" * (-len(kept) % 4))
    check("decoded: far too short to be a certificate", len(raw) < 200, f"{len(raw)} bytes")
    check("decoded: is not recognised as one", not is_pinned_certificate(candidate.encode()), "still parses as a cert")


def test_is_pinned_certificate() -> None:
    """Only full-length Base64 PEM blobs count as pins."""
    pem = b"-----BEGIN CERTIFICATE-----\n" + b"QUJD" * 80 + b"\n-----END CERTIFICATE-----\n"
    encoded = base64.b64encode(pem)
    check("detector: real PEM", is_pinned_certificate(encoded), "missed a certificate")
    check("detector: truncated copy", not is_pinned_certificate(encoded[:136]), "accepted a prefix")
    check("detector: random text", not is_pinned_certificate(b"hello world" * 40), "false positive")


def test_unfixable_neighbours() -> None:
    """With neighbours that share no prefix the tool must refuse, not guess."""
    pin = PIN
    try:
        build_replacement(pin, "ZZZZsomething-else", FOLLOWING)
    except PatchError:
        check("refuses when no prefix fits", True)
    else:
        check("refuses when no prefix fits", False, "returned a replacement anyway")


def main() -> int:
    """Run every test and report."""
    for test in (
        test_mutf8_order,
        test_replacement_stays_sorted,
        test_replacement_decodes_to_nonsense,
        test_is_pinned_certificate,
        test_unfixable_neighbours,
    ):
        print(f"\n== {test.__name__}")
        test()
    print()
    if failures:
        print(f"{len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
