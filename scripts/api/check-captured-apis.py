#!/usr/bin/env python3
"""Check the route table against the transcripts.

The transcripts in `data/flows/` hold the requests the app made and the
answers it got from the reference deployment and from Bumper. This script
answers the question the route table cannot answer on its own: **what does
the app call that Bumper does not serve?**

    ./scripts/api/check-captured-apis.py

The transcripts are written by `scripts/api/1-convert-mitmproxy-flows-export.py`
and are not committed, so this is a local tool. The route table itself is
pinned by `tests/web/routes.txt`.
"""

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[2]))


#: The repository, so the tool can be called from anywhere.
REPO_ROOT = Path(__file__).parents[2]

FLOWS_DIR = REPO_ROOT / "data/flows"

# The flow header lines look like:
#   [1] 2025-04-27T15:01:44.330Z  POST https://host/path?query  (HTTP/2.0)
URL_RE = re.compile(r"\]\s+\S+\s+((?:GET|POST|PUT|DELETE|PATCH|HEAD)\s+https?://\S+)")

# Only the Ecovacs API surface is in scope. Paths served from a CDN, from
# Aliyun, or from a wholly different product are out of scope: Bumper is not
# meant to impersonate them.
IN_SCOPE_PREFIXES = (
    "/api/",
    "/v0.1/",
    "/v1/",
    "/v2/",
    "/v3/",
    "/app/",
    "/app_adv/",
    "/pim/",
    "/public/",
    "/global/",
    "/Global_APP_BuryPoint",
    "/biz-app-config/",
    "/newauth.do",
    "/lookup.do",
    "/config/Android.conf",
    "/data_collect/",
)


def normalise(path: str) -> str:
    """Reduce a captured path to something matchable against the route table.

    The private API embeds per-client segments, which vary per client and per
    app version. Collapse exactly those and keep the version prefix, so the
    comparison is about the endpoint rather than the session.
    """
    path = path.split("?", 1)[0]
    path = re.sub(r"^(/v[0-9.]+/private/)(?:[^/]+/){7}", r"\1<VARS>/", path)
    return path or "/"


def normalise_pattern(pattern: str) -> str:
    """Reduce a route pattern the way a captured path is reduced."""
    return re.sub(r"^(/v[0-9.]+/private/)(?:\{[^}]+\}/){7}", r"\1<VARS>/", pattern)


def route_paths() -> list[str]:
    """Return every path the server serves.

    The plugins carry the Ecovacs surface, `server.py` registers the handful
    of paths that are not plugins (`/newauth.do`, the CodePush reports, the
    data sink), so the app itself is the source of truth.
    """
    from bumper.web.server import WebServer, WebserverBinding

    server = WebServer(WebserverBinding("127.0.0.1", 8007, False), False)
    paths: list[str] = []
    for resource in server._app.router.resources():
        info = resource.get_info()
        if (app := info.get("app")) is not None:
            paths.extend(_paths_of(app.router))
            continue
        paths.extend(resource.canonical for _ in resource)
    return paths


def _paths_of(router: Any) -> list[str]:
    """Return the paths of a router and of the sub apps under it."""
    paths: list[str] = []
    for resource in router.resources():
        info = resource.get_info()
        if (app := info.get("app")) is not None:
            paths.extend(_paths_of(app.router))
            continue
        paths.extend(resource.canonical for _ in resource)
    return paths


def matches(path: str, served: list[str]) -> bool:
    """Report whether a captured path is served."""
    for pattern in served:
        regex = re.sub(r"\{[^}]+\}", "(.*?)", pattern)
        if re.fullmatch(regex, path):
            return True
    return False


def main() -> None:
    """Compare the captured paths with the route table."""
    if not FLOWS_DIR.is_dir():
        msg = f"no transcripts in {FLOWS_DIR} - run scripts/api/1-convert-mitmproxy-flows-export.py first"
        print(msg)
        return

    served = [normalise_pattern(path) for path in route_paths()]
    tally: Counter[str] = Counter()
    sources: dict[str, set[str]] = {}
    out_of_scope = 0

    for flow in sorted(FLOWS_DIR.glob("*-clean")):
        text = flow.read_text(errors="replace")
        for match in URL_RE.finditer(text):
            url = match.group(1).split(" ", 1)[1]
            host_and_path = re.sub(r"^https?://[^/]+", "", url)
            path = normalise(host_and_path)
            if not path.startswith("/"):
                continue
            if not path.startswith(IN_SCOPE_PREFIXES):
                out_of_scope += 1
                continue
            tally[path] += 1
            sources.setdefault(path, set()).add(flow.name)

    missing = [(count, path) for path, count in tally.items() if not matches(path, served)]
    missing.sort(reverse=True)

    print(f"in-scope captured paths : {len(tally)}   (ignored {out_of_scope} out-of-scope calls)")
    print(f"served by Bumper       : {len(tally) - len(missing)}")
    print(f"NOT served by Bumper   : {len(missing)}")
    print()
    print("captured but not served (ranked by call count):")
    for count, path in missing:
        names = ", ".join(sorted(sources[path]))
        print(f"  {count:5}  {path}   [{names}]")


if __name__ == "__main__":
    main()
