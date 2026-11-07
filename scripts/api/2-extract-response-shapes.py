#!/usr/bin/env python3
"""Write the response shapes of the API.

The transcripts in `data/flows/` hold the requests the app made and the
answers it got. The converter writes them there, and the directory is local
working data that is not committed. Two groups of them:

- `flows-cloud-*` are the official reference answers. They are
  the fidelity oracle: the shapes the app has to find.
- `flows-bumper-*` are the answers this server gave. They are the regression
  oracle: the shapes the app already knows.

This script extracts the shape of each answer - the keys it carries and the
type of each - into a candidate set. By default it only previews what would be
added. `--write` merges observations into the committed fixtures without
removing existing evidence. `--replace` explicitly rebuilds fixtures from all
matching local transcripts, so use it only when that transcript set is complete.

    ./scripts/api/2-extract-response-shapes.py           # preview
    ./scripts/api/2-extract-response-shapes.py --write   # additive update
    ./scripts/api/2-extract-response-shapes.py --replace # explicit rebuild

The transcripts are not committed, so this is a local tool. The files it
writes are.
"""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

#: The repository, so the tool can be called from anywhere.
REPO_ROOT = Path(__file__).parents[2]

FLOWS_DIR = REPO_ROOT / "data/flows"

#: The reference answers, and the file they go into.
OFFICIAL = ("flows-cloud-*", REPO_ROOT / "tests/web/response_shapes.json")
#: The answers of this server, and the file they go into.
BUMPER = ("flows-bumper-*", REPO_ROOT / "tests/web/response_shapes_bumper.json")

# The private API carries the client in the path; the endpoint is what is
# left of it.
PRIVATE = re.compile(r"^(/v[0-9.]+/private/)(?:[^/]+/){7}")

# The paths of the API. Everything else (the images, the web pages, the
# third party hosts) is out of scope.
IN_SCOPE = ("/api/", "/v0.1/", "/v1/", "/v2/", "/v3/", "/app/", "/newauth.do")

# The hosts of Ecovacs. The app talks to other hosts as well - the push
# service, the analytics - and those are not the API of Bumper.
ECOVACS = (".ecouser.net", ".ecovacs.com")

REQUEST_LINE = re.compile(r"^\[\d+\]\s+\S+\s+(GET|POST|PUT|DELETE|PATCH|HEAD)\s+(\S+)", re.MULTILINE)
BODY = re.compile(r"^body: \d+ bytes[^\n]*\n-+\n(.*?)\n-+$", re.DOTALL | re.MULTILINE)
RESPONSE = re.compile(r"^RESPONSE (\d{3})", re.MULTILINE)


def blocks(text: str) -> list[str]:
    """Split a transcript into its flows."""
    return re.split(r"^={20,}$", text, flags=re.MULTILINE)


def shape(body: Any) -> dict[str, str]:
    """Return the keys of an answer and the type of each."""
    if not isinstance(body, dict):
        return {}
    return {key: type(value).__name__ for key, value in sorted(body.items())}


def normalise(path: str) -> str:
    """Reduce a path to the endpoint it names."""
    path = path.split("?", 1)[0]
    return PRIVATE.sub(r"\1<VARS>/", path)


def operation_of(request_body: str) -> str:
    """Return the operation the request names, if it names one."""
    if "=" in request_body and "{" not in request_body:
        fields = parse_qs(request_body)
        return str(fields.get("todo", fields.get("td", [""]))[0])
    try:
        fields = json.loads(request_body)
    except ValueError:
        return ""
    if isinstance(fields, dict):
        return str(fields.get("todo", fields.get("td", "")) or "")
    return ""


def collect(patterns: tuple[str, ...]) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Return the shape of every answer of the transcripts of a group."""
    shapes: dict[str, dict[str, list[dict[str, str]]]] = {}

    for pattern in patterns:
        flows = sorted(FLOWS_DIR.glob(pattern))
        for flow in flows:
            if not flow.is_file() or flow.suffix in {".json", ".mitm"}:
                continue
            text = flow.read_text(errors="replace")
            if not text.startswith("# mitmproxy flow transcript"):
                continue
            for block in blocks(text):
                request = REQUEST_LINE.search(block)
                if request is None:
                    continue
                method, url = request.group(1), request.group(2)
                parsed = urlparse(url)
                if not parsed.netloc.endswith(ECOVACS):
                    continue
                path = normalise(parsed.path)
                if not path.startswith(IN_SCOPE):
                    continue

                response = RESPONSE.search(block)
                if response is None or response.group(1) != "200":
                    continue

                bodies = BODY.findall(block)
                if not bodies:
                    continue
                # A request without a body (a GET) has only the answer.
                request_body = bodies[-2] if len(bodies) > 1 else ""
                response_body = bodies[-1]

                try:
                    answer = json.loads(response_body)
                except ValueError:
                    continue

                operation = operation_of(request_body)
                key = f"{path}#{operation}" if operation else path
                seen = shapes.setdefault(key, {}).setdefault(method, [])
                if shape(answer) not in seen:
                    seen.append(shape(answer))

    return {key: value for key, value in sorted(shapes.items()) if value}


def merge_shapes(
    existing: dict[str, dict[str, list[dict[str, str]]]],
    observed: dict[str, dict[str, list[dict[str, str]]]],
) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Add observed shapes without removing previously recorded evidence."""
    merged: dict[str, dict[str, list[dict[str, str]]]] = {}
    for source in (existing, observed):
        for endpoint, methods in source.items():
            for method, variants in methods.items():
                collected = merged.setdefault(endpoint, {}).setdefault(method, [])
                for variant in variants:
                    if variant not in collected:
                        collected.append(variant)

    return {
        endpoint: {
            method: sorted(variants, key=lambda variant: json.dumps(variant, sort_keys=True))
            for method, variants in sorted(methods.items())
        }
        for endpoint, methods in sorted(merged.items())
    }


def load_shapes(path: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Load a shape fixture, treating a missing file as an empty fixture."""
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    """Preview, add, or explicitly replace the captured shape fixtures."""
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--write", action="store_true", help="add observed shapes without removing existing ones")
    action.add_argument("--replace", action="store_true", help="replace fixtures with shapes from all matching local transcripts")
    args = parser.parse_args()

    if not FLOWS_DIR.is_dir():
        msg = f"no transcripts in {FLOWS_DIR} - run scripts/api/1-convert-mitmproxy-flows-export.py first"
        print(msg, file=sys.stderr)
        return 1

    for patterns, target in ((OFFICIAL[:1], OFFICIAL[1]), (BUMPER[:1], BUMPER[1])):
        observed = collect(patterns)
        if not observed:
            print(f"no observed shapes for {target.name}; left unchanged")
            continue

        existing = load_shapes(target)
        result = observed if args.replace else merge_shapes(existing, observed)
        added = sum(
            len(variants) - len(existing.get(endpoint, {}).get(method, []))
            for endpoint, methods in result.items()
            for method, variants in methods.items()
        )
        action_name = "replace" if args.replace else "merge"

        if not args.write and not args.replace:
            print(f"preview: {len(observed)} observed endpoint shapes for {target.name}; {added} new variants")
            print(f"run with --write to merge into {target}, or --replace to rebuild it from all local transcripts")
            continue

        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{action_name}: {len(result)} endpoint shapes, {added} new variants -> {target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
