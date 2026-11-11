#!/usr/bin/env python3
"""Keep MkDocs/Zensical admonitions stable under Prettier.

Prettier does not know about ``!!!`` admonitions. If the body starts on the
line directly below the marker, Prettier reads the marker and the first body
paragraph as one paragraph and removes the indentation, which breaks rendering.

A blank line between the marker and the body prevents that. After Prettier has
already dedented a body, the script restores the indentation as well, so it can
repair an existing file and then keep it stable.
"""

import pathlib
import re
import sys

# Lines that start a new block and therefore never belong to an admonition body.
_BLOCK_START = re.compile(r"^\s*(?:!!!|#{1,6}(?:\s|$)|(?:-{3,}|\*{3,}|_{3,})\s*$)")
_MARKER = re.compile(r"^(\s*)!!!")


def _indent_body(lines: list[str], start: int, body: str) -> int:
    """Indent the paragraph at ``start`` and return the index after it."""
    cursor = start
    while cursor < len(lines):
        current = lines[cursor]
        if not current.strip() or _BLOCK_START.match(current) or current.startswith(body):
            break
        lines[cursor] = body + current.lstrip(" ")
        cursor += 1
    return cursor


def fix(text: str) -> str:
    """Return ``text`` with every admonition body separated and indented."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = _MARKER.match(lines[index])
        if match is None:
            index += 1
            continue
        body = " " * (len(match.group(1)) + 4)
        after = index + 1
        if after < len(lines) and lines[after].strip():
            _indent_body(lines, after, body)
            lines.insert(after, "")
        else:
            while after < len(lines) and not lines[after].strip():
                after += 1
            if after < len(lines):
                _indent_body(lines, after, body)
        index += 1
    result = "\n".join(lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def main(argv: list[str]) -> int:
    """Normalize every path given on the command line."""
    changed = False
    for name in argv[1:]:
        path = pathlib.Path(name)
        text = path.read_text(encoding="utf-8")
        fixed = fix(text)
        if fixed != text:
            path.write_text(fixed, encoding="utf-8")
            changed = True
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
