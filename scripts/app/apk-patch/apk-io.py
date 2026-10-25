"""Shared APK zip I/O for the two patchers.

Both patchers rewrite one or more entries and drop the old v1 signature files,
which is the same operation, so it lives here once.
"""

from pathlib import Path
import zipfile

# v1 signature files. They are not checked on modern Android, but they become
# invalid as soon as a patched entry changes.
SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def is_signature_entry(name: str) -> bool:
    """Return True for a v1 signature file inside META-INF/."""
    upper = name.upper()
    return upper.startswith("META-INF/") and upper.endswith(SIGNATURE_SUFFIXES)


def repack(src: Path, dst: Path, replacements: dict[str, bytes]) -> None:
    """Copy `src` to `dst`, swapping in `replacements` and dropping signatures.

    `replacements` maps archive entry name to new bytes; every other entry is
    copied unchanged, keeping its original compression.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            if is_signature_entry(info.filename):
                continue
            data = replacements.get(info.filename, zin.read(info))
            zout.writestr(info, data, compress_type=info.compress_type)
