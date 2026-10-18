#!/usr/bin/env python3
"""Set ``android:debuggable="true"`` in an APK's binary AndroidManifest.xml.

The Ecovacs app ships a ``network_security_config.xml`` containing::

    <debug-overrides>
        <trust-anchors><certificates src="user"/></trust-anchors>
    </debug-overrides>

Android applies ``<debug-overrides>`` to every domain, but only to a debuggable
app. Setting the flag is what makes the platform trust a **user-installed CA**,
which is how Bumper's self-signed certificate is accepted.

MQTT is the one channel that ignores this; ``patch_mqtt_trust.py`` handles it.

The edit follows the AXML layout used by aapt/apktool: append a string to the
pool, extend the resource map so the attribute id resolves, and splice a 20-byte
attribute record into the ``<application>`` start element.

Usage:
    patch_debuggable.py <in.apk> <out.apk> [--force]
"""

import argparse
import struct
import sys
import zipfile
from pathlib import Path

from apk_io import repack as repack_apk

CHUNK_STRING_POOL = 0x001
CHUNK_XML = 0x003
CHUNK_START_ELEMENT = 0x102
CHUNK_RESOURCE_MAP = 0x180

ATTR_TYPE_BOOL = 0x12
ATTR_DEBUGGABLE = 0x0101_000F  # android.R.attr.debuggable
ATTR_FORMAT = "<IIiHBBi"  # namespace, name, rawValue, size, res0, type, data
ATTR_SIZE = struct.calcsize(ATTR_FORMAT)
START_ELEMENT_HEADER = "<HHIIIIIIHHHH"

DEBUGGABLE = "debuggable"


class PatchError(Exception):
    """The manifest cannot be patched safely."""


class ChunkHeader:
    __slots__ = ("type", "header_size", "size", "data", "header_only")

    def __init__(self, type_: int, header_size: int, size: int, data: bytes, header_only: bool = False) -> None:
        self.type = type_
        self.header_size = header_size
        self.size = size
        self.data = data
        self.header_only = header_only

    @classmethod
    def read(cls, blob: bytes, offset: int, header_only: bool = False) -> "tuple[ChunkHeader, int]":
        type_, header_size, size = struct.unpack_from("<HHI", blob, offset)
        end = offset + (header_size if header_only else size)
        return cls(type_, header_size, size, blob[offset:end], header_only), end

    def to_bytes(self) -> bytes:
        body = bytearray(self.data)
        if not self.header_only:
            body[4:8] = struct.pack("<I", len(body))
        return bytes(body)


class StringPool:
    """AXML string pool, sufficient for appending one ASCII string."""

    def __init__(self, header: ChunkHeader) -> None:
        self.header = header
        blob = header.data
        # Header: type(2) headerSize(2) chunkSize(4) stringCount(4) styleCount(4)
        #         flags(4) stringsStart(4) stylesStart(4)
        string_count, style_count, flags, strings_offset, styles_offset = struct.unpack_from("<IIIII", blob, 8)
        self.utf8 = bool(flags & (1 << 8))
        self.string_count = string_count
        self.style_count = style_count
        self.strings_offset = strings_offset
        self.styles_offset = styles_offset
        self.header_size = 28
        base = self.header_size
        self.offsets = [struct.unpack_from("<I", blob, base + 4 * i)[0] for i in range(string_count)]

    def get(self, index: int) -> str | None:
        if not 0 <= index < len(self.offsets):
            return None
        blob = self.header.data
        # `header.data` starts at the chunk, so this is a chunk-relative lookup.
        pos = self.strings_offset + self.offsets[index]
        if self.utf8:
            n = blob[pos]
            pos += 1
            if n & 0x80:
                pos += 1
            n = blob[pos]
            pos += 1
            if n & 0x80:
                n = ((n & 0x7F) << 8) | blob[pos]
                pos += 1
            return blob[pos : pos + n].decode("utf-8", "replace")
        n = struct.unpack_from("<H", blob, pos)[0]
        pos += 2
        return blob[pos : pos + n * 2].decode("utf-16-le", "replace")

    def append(self, value: str) -> int:
        blob = bytearray(self.header.data)
        if self.utf8:
            encoded = value.encode("utf-8")
            if len(value) >= 0x80 or len(encoded) >= 0x80:
                raise PatchError("multi-byte string pool entries are not supported")
            entry = struct.pack("<BBB", len(value), len(encoded), 0) + encoded
        else:
            encoded = value.encode("utf-16-le")
            entry = struct.pack("<H", len(value)) + encoded + b"\x00\x00"

        # A new offset entry is inserted after the existing ones, shifting the
        # string data by 4 bytes; `stringsStart` moves to match. The string bytes
        # go at the end of the chunk.
        end = self.header_size + self.string_count * 4
        out = bytearray(self.header.data)
        out[end:end] = b"\x00\x00\x00\x00"  # placeholder for the new offset

        # Each string entry must start 4-byte aligned.
        out.extend(b"\x00" * ((4 - len(out) % 4) % 4))
        offset = len(out) - (self.strings_offset + 4)
        out.extend(entry)
        out.extend(b"\x00" * ((4 - len(out) % 4) % 4))

        struct.pack_into("<I", out, end, offset)
        self.string_count += 1
        struct.pack_into("<I", out, 8, self.string_count)
        self.strings_offset += 4
        struct.pack_into("<I", out, 20, self.strings_offset)
        if self.styles_offset:
            self.styles_offset += 4
            struct.pack_into("<I", out, 24, self.styles_offset)
        self.header.data = bytes(out)
        return self.string_count - 1


class ResourceMap:
    """Maps string-pool indices to android framework attribute ids."""

    def __init__(self, header: ChunkHeader) -> None:
        self.header = header

    def get(self, index: int) -> int:
        """Return the attribute id for a string-pool index, 0 when out of range."""
        offset = index * 4 + 8
        if offset + 4 > len(self.header.data):
            return 0
        return int.from_bytes(self.header.data[offset : offset + 4], "little")

    def add_debuggable(self, index: int) -> None:
        data = bytearray(self.header.data)
        target = (index + 1) * 4
        current = len(data) - 8
        if current > target:
            raise PatchError("resource map already covers this attribute")
        data.extend(b"\x00" * (target - current - 4))
        data.extend(struct.pack("<I", ATTR_DEBUGGABLE))
        self.header.data = bytes(data)


def _splice_attribute(chunk: ChunkHeader, name_index: int, resource_map: ResourceMap) -> None:
    data = bytearray(chunk.data)
    attr_count = struct.unpack_from("<H", data, 28)[0]
    # The <application> tag always has >=1 attribute; use the previous one for the namespace.
    if attr_count < 1:
        raise PatchError("<application> has no attributes; cannot infer the android namespace")
    prev = len(data) - ATTR_SIZE
    namespace = struct.unpack_from("<I", data, prev)[0]
    if namespace == 0 and attr_count > 1:
        namespace = struct.unpack_from("<I", data, prev - ATTR_SIZE)[0]

    record = struct.pack(ATTR_FORMAT, namespace, name_index, -1, 8, 0, ATTR_TYPE_BOOL, -1)
    # Some parsers require the attributes sorted by resource id.
    insert_at = len(data)
    for pos in range(attr_count + 1):
        off = 36 + ATTR_SIZE * pos
        if off + ATTR_SIZE > len(data):
            break
        idx = int.from_bytes(data[off + 4 : off + 8], "little")
        if resource_map.get(idx) > ATTR_DEBUGGABLE:
            insert_at = off
            break
    data[insert_at:insert_at] = record

    attr_count += 1
    struct.pack_into("<H", data, 28, attr_count)
    struct.pack_into("<I", data, 4, len(data))
    chunk.data = bytes(data)


def _split_chunks(blob: bytes) -> tuple[ChunkHeader, list[ChunkHeader]]:
    """Split a binary-XML blob into its root header and its child chunks.

    The root chunk's `size` covers the whole file, so only its header is kept.
    """
    root, offset = ChunkHeader.read(blob, 0, header_only=True)
    if root.type != CHUNK_XML:
        msg = "not a binary XML file"
        raise PatchError(msg)
    children: list[ChunkHeader] = []
    offset = root.header_size
    while offset < len(blob):
        chunk, offset = ChunkHeader.read(blob, offset)
        children.append(chunk)
    return root, children


def debuggable_value(blob: bytes) -> bool | None:
    """Return the `android:debuggable` value on `<application>`, None if absent.

    Re-parses the manifest with this module's own reader, so verifying needs no
    third-party XML library.
    """
    _, chunks = _split_chunks(blob)
    pool: StringPool | None = None
    resource_map: ResourceMap | None = None
    for chunk in chunks:
        if chunk.type == CHUNK_STRING_POOL and pool is None:
            pool = StringPool(chunk)
        elif chunk.type == CHUNK_RESOURCE_MAP and resource_map is None:
            resource_map = ResourceMap(chunk)
        elif chunk.type == CHUNK_START_ELEMENT and resource_map is not None and pool is not None:
            name = pool.get(struct.unpack_from("<I", chunk.data, 20)[0])
            if name != "application":
                continue
            attr_count = struct.unpack_from("<H", chunk.data, 28)[0]
            for pos in range(attr_count):
                offset = 36 + ATTR_SIZE * pos
                *_, attr_name, _, _, _, _, value = struct.unpack_from(ATTR_FORMAT, chunk.data, offset)
                if resource_map.get(attr_name) == ATTR_DEBUGGABLE:
                    return value == -1
            return None
    return None


def patch_manifest(blob: bytes) -> bytes:
    root, chunks = _split_chunks(blob)
    chunks.insert(0, root)

    pool: StringPool | None = None
    resource_map: ResourceMap | None = None
    name_index: int | None = None
    patched = False

    for chunk in chunks:
        if chunk.type == CHUNK_STRING_POOL and pool is None:
            pool = StringPool(chunk)
            name_index = pool.append(DEBUGGABLE)
        elif chunk.type == CHUNK_RESOURCE_MAP and resource_map is None:
            resource_map = ResourceMap(chunk)
            resource_map.add_debuggable(name_index)
        elif chunk.type == CHUNK_START_ELEMENT and resource_map is not None and pool is not None:
            name = pool.get(struct.unpack_from("<I", chunk.data, 20)[0])
            if name == "application" and not patched:
                if _already_debuggable(chunk, name_index):
                    return blob
                _splice_attribute(chunk, name_index, resource_map)
                patched = True

    if not patched:
        raise PatchError("no <application> element found")

    children = b"".join(c.to_bytes() for c in chunks[1:])
    # The root chunk's size field covers the entire file, so refresh it.
    root_data = bytearray(root.data)
    root_data[4:8] = struct.pack("<I", root.header_size + len(children))
    return bytes(root_data) + children


def _already_debuggable(chunk: ChunkHeader, name_index: int) -> bool:
    attr_count = struct.unpack_from("<H", chunk.data, 28)[0]
    for pos in range(attr_count):
        off = 36 + ATTR_SIZE * pos
        _, name, _, _, _, _, _ = struct.unpack_from(ATTR_FORMAT, chunk.data, off)
        if name == name_index:
            return True
    return False


def repack(src: Path, dst: Path, manifest: bytes) -> None:
    repack_apk(src, dst, {"AndroidManifest.xml": manifest})


def verify(path: Path) -> bool:
    """Confirm the written APK's manifest still parses and debuggable=true."""
    try:
        with zipfile.ZipFile(path) as archive:
            blob = archive.read("AndroidManifest.xml")
        return debuggable_value(blob) is True
    except (OSError, KeyError, IndexError, PatchError, struct.error, zipfile.BadZipFile):
        return False


def main(argv: list[str] | None = None) -> int:
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

    try:
        with zipfile.ZipFile(args.src) as z:
            manifest = z.read("AndroidManifest.xml")
        patched = patch_manifest(manifest)
        repack(args.src, args.dst, patched)
    except (PatchError, KeyError, zipfile.BadZipFile, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"patched {args.src.name} -> {args.dst}")
    if verify(args.dst):
        print('verified: android:debuggable="true" present, manifest still parses')
    else:
        print("error: post-patch verification failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
