#!/usr/bin/env python3
"""Check the APKs a build produced: present, signed, and reporting their ABIs.

Run by build-apks.sh against the directory the signed splits were written to.
"""

from __future__ import annotations

import pathlib
import sys
import zipfile

SIGNATURE_SUFFIXES = (".RSA", ".DSA")


def signed(names: list[str]) -> bool:
    """Return True when the archive carries a v1 signature."""
    if "META-INF/ANDROIDD.SF" in names:
        return True
    return any(n.startswith("META-INF/") and n.endswith(SIGNATURE_SUFFIXES) for n in names)


def main() -> int:
    """Report on every APK in the given directory."""
    out = pathlib.Path(sys.argv[1])
    apks = sorted(out.glob("*.apk"))
    if not apks:
        msg = "no APKs produced"
        raise SystemExit(f"❌ {msg}")

    abis: set[str] = set()
    for apk in apks:
        with zipfile.ZipFile(apk) as archive:
            names = archive.namelist()
            found = sorted({n.split("/")[1] for n in names if n.startswith("lib/")})
        if not signed(names):
            msg = f"{apk.name}: unsigned"
            raise SystemExit(f"❌ {msg}")
        abis.update(found)
        where = f"lib/{', lib/'.join(found)}" if found else "no native code"
        print(f"   ✓ {apk.name} ({apk.stat().st_size // 1024} KiB) - {where}")

    print(f"   ✓ {len(apks)} file(s) signed and ready")
    if abis:
        print(f"   ⚠️  Native code is only in the ABI split ({', '.join(sorted(abis))}).")
        print("      The account screens are React Native and its SoLoader looks up")
        print("      lib/<first device ABI> only, so they need a device whose primary ABI is one of:")
        print(f"      {', '.join(sorted(abis))}.")
        print("      Anything else gets a blank login screen: no other ABI is published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
