# AGENTS.md

Instructions for AI agents and human contributors working in this repository.

## What this project is

Bumper is a **self-hosted replacement for the Ecovacs cloud**. It reimplements the
server side of the Ecovacs ecosystem so Deebot robots and the Ecovacs app talk only
to your LAN - nothing reaches Ecovacs' servers.

It terminates three protocols and brokers between them:

| Service     | Module        | Default ports    | Role                                          |
| ----------- | ------------- | ---------------- | --------------------------------------------- |
| Web server  | `bumper/web`  | 443, 8007        | Ecovacs REST API clone + Bumper's own web UI  |
| XMPP server | `bumper/xmpp` | 5223 (TLS), 1223 | Relays XML stanzas between app and robot      |
| MQTT broker | `bumper/mqtt` | 8883 (TLS), 1883 | Telemetry/command topics, plus the helper bot |

Because the app and robots must work unmodified, **fidelity to the observed Ecovacs
API is the primary requirement.** Do not "clean up" response shapes, status codes,
field names, or endpoint paths - the clients depend on them. When you touch a
handler, prefer matching observed traffic over the cleanest-looking code.

## Commands

Run everything through `uv`; the lockfile is committed and CI uses `--locked`.

```sh
uv sync --all-groups            # install dev deps
uv run bumper                   # start the server

uv run --frozen ruff check bumper/
uv run --frozen ruff format --check bumper/
uv run --frozen mypy bumper/    # strict mode, see pyproject.toml
uv run --frozen pylint bumper/
uv run pytest tests
prek run --all-files           # mirrors the full CI lint stage
```

`prek` is the pre-commit runner; mypy and pylint run as prek hooks via
`scripts/run-in-dev-env.sh`, so they are skipped locally on files in `tests/`,
`scripts/`, and `configs/`.

Run the three linters and pytest before opening a PR - CI gates on all of them.

## Conventions

**Config**

- All configuration is environment-driven and declared as class attributes in
  `bumper/utils/settings.py`. Add new settings there, not by reading `os.environ`
  at the call site. Import the singleton as `from bumper.utils.settings import config as bumper_isc`.
- The `docs/configuration/environment.md` table is maintained by hand - update it
  in the same change when you add or change a variable.
- Bools go through `str_to_bool`; ports through `int(...)`.

**Python / style**

- Python 3.13+ (`requires-python`); CI runs 3.13 and 3.14. Modern typing is
  mandatory: `X | None`, built-in generics, `from __future__ import annotations`
  is not needed and not used.
- Every module, class, and function needs a docstring. `ruff` runs with
  `select = ["ALL"]` and line length 130 - the ignore list is short, so expect
  new lint hits rather than exemptions.
- Strings are formatted lazily: assign to a variable and `raise`/`return` it,
  since `EM101`/`TRY003` are active.

**Logging**

- `SanitizeFilter` (`bumper/utils/log_helper.py`) redacts by **substring**, not by
  key: `auth`, `did`, `email`, `login`, `mobile`, `token`, `uid`, `user`. Any log
  string containing one of those is replaced wholesale, and any dict _value_ under
  such a key is replaced. So `candidate_type` is redacted - "candidate" contains
  "did" - and a JSON blob containing "embedded" dies with it. Pick field names
  that avoid the list, or log a dict instead of a pre-serialized string.
- The filter **mutates the record in place**, so a log line can look different
  depending on which handlers ran before the one you read. Do not assert on
  sanitized output in a test without applying the filter yourself first.

**Web layer**

- Routes are **auto-discovered**. A module under `bumper/web/plugins/` is
  imported and registered purely by its location; any class in it that subclasses
  `WebserverPlugin` has its `routes` property added to the aiohttp app. Directory
  names become URL path prefixes (`bumper/web/plugins/v2/private/` → `/v2/private/`).
  Adding an endpoint usually means adding a method to an existing plugin class, not
  editing a router.
- `bumper/web/web_paths.py` is separate and hand-registered - it is Bumper's own
  UI, not the Ecovacs API surface.
- aiohttp matches paths **case-sensitively**, and the app is not consistent
  about casing (it posts CodePush status to both `report_status` and
  `report_Status`). When observed traffic shows a variant, register each one
  explicitly rather than assuming one covers the other.
- The middleware decides whether a request is served by asking the aiohttp
  router (`request.match_info.route.resource is None` means "not covered"),
  which cannot drift from the route table. Set
  `DEBUG_LOGGING_API_REQUEST_MISSING=true` to see only those.

**Persistence**

- Storage is TinyDB (JSON), not SQLite. Repos in `bumper/db/` subclass `BaseRepo`
  and are exposed as module-level singletons (`bot_repo`, `client_repo`,
  `user_repo`, `token_repo`, `clean_log_repo`) from `bumper.db`. Use the
  `_get`/`_upsert`/`_remove` helpers rather than touching `Table` directly.
- Schema changes need a migration entry in `bumper/db/migration.py`. The migration
  chain keys off the app version and writes a timestamped `.bak` next to the
  database automatically - add the step, don't hand-edit data.

**TLS**

- Certs are self-signed and generated at startup (`bumper/utils/certs.py`).
  Bot/app trust depends on the CA, so treat anything touching cert generation,
  SANs, or the CA archive as security-sensitive.

## Testing

- Tests live in `tests/` mirroring the package layout (`tests/db`, `tests/mqtt`,
  `tests/web/plugins/...`, `tests/xmpp`, `tests/utils`). Mirror the source path.
- `asyncio_mode = "auto"`; async tests need no decorator. A 10s per-test timeout
  is enforced globally, and `tests/conftest.py` runs `tracemalloc` for leak checks.
- `tests/conftest.py` provides real server fixtures (MQTT/XMPP/web on fixed
  ports) - prefer them over mocking aiohttp/amqtt.
- Tests must not depend on network access or a real robot.

## Ecovacs app communication model

Facts about how the official app reaches Ecovacs, which constrain what Bumper has
to emulate. These change how a new endpoint should be written - read them before
adding a handler.

**Two API generations are in use at once.**

|          | Legacy                                                                         | Modern                                                                                                                                       |
| -------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Hosts    | `*.ecouser.net` (`portal`, `api-app`, `lb<region>`, `msg`, `mq`)               | `*.ecovacs.com` (`gl-<network>-<country>-api`, `-openapi`)                                                                                   |
| Auth     | headers `appid`, `ts`, `sign`, `token`; `sign = SHA1(appid + APP_SECRET + ts)` | query params `authAppkey`, `authTimespan`, `authTimeZone`, `requestId`, `authSign`; `authSign = digest(appkey + sorted(k=v, k=v…) + secret)` |
| Envelope | `ret`/`errno`; `"ok"` or error code                                            | `code`; `"0000"` success                                                                                                                     |

`lb<region>.ecouser.net` is a per-region shard - the client is handed the
concrete hostname by the portal at runtime, so do not assume a single `lb` host.
Region routing (which portal, which `lb` shard, which language) is driven by
`assets/app_config_domain.json` inside the app.

**The NGIoT bridge is a third envelope family.** `/api/iot/endpoint/control`
does not answer with a JSON error document: it answers HTTP 200 with an empty
body and carries the outcome in the `x-ngiot-*` headers. The app reads those
headers, so a JSON error body makes an offline robot indistinguishable from a
broken server. `x-ngiot-fmt: b` is returned even for JSON payloads - that is
what the real server does, do not "fix" it. An offline robot is
`x-ngiot-errno: 4200` / `x-ngiot-ret: error`. The request's `ct` selects the
variant: `q` is request/response, `m` is fire-and-forget (ack, no robot
answer). See `response_ngiot_*` in `bumper/web/utils/response_helper.py`.

**Time skew matters.** The modern API answers a stale clock with `code == "0005"`
plus the server time; the client stores the offset, replays the request once,
and persists it. Any handler that returns `0005` must include a `time` field,
and Bumper's clock should be sane.

**CodePush ships app logic, not just assets.** The app's JS bundles are delivered
per deployment key, so `updateCheck.json` + `updateCheck_mapping.json` are live
inputs to app behavior, not inert fixtures. The recorded `target_binary_range`
is `"1.0.0"` throughout; a stale or mismatched entry can make the app render
incorrectly. Treat drift here as a bug class of its own, distinct from
`web/plugins/` fidelity.

**The account screens are React Native, and Hermes is mandatory.** They only
render if `ReactNativePreLoader.create()` succeeds, which needs `SoLoader.init()`
and the Hermes load (`libhermes.so`). RN and Hermes are already present in
3.11.0, not just 3.12+, so downgrading the app does not avoid this. There are two
consequences:

- **A white/blank screen there is usually not a Bumper problem.**
  `base.apk` carries **no native code at all** - every `.so`, including
  `libhermes.so`, lives in the per-ABI split - and SoLoader only ever searches
  `lib/<SUPPORTED_ABIS[0]>` inside the APKs (one ABI, not a loop). The app
  publishes no x86_64 build at any version, so on an x86_64 emulator
  `SUPPORTED_ABIS[0]` is `x86_64` and nothing matches: the log shows
  `DirectApkSoSource` looking at `lib/x86_64` in all four APKs and nothing else,
  then a hard `FATAL EXCEPTION` out of `EcoMainActivity.onCreate` ->
  `EcoReactView.bindView` -> `ReactNativePreLoader.create` ->
  `HermesExecutor.<clinit>`. The activity dies mid-`onCreate`, which is the white
  screen. This cannot be fixed from Bumper's side - it needs an arm64 device or
  an arm64 (emulated) system image.
- The RN network module (`IgnoreSSLFactory`) is trust-all, so RN traffic is not a
  TLS concern.

**Apart from MQTT, the app pins nothing.** So the `scripts/create-unpinned-app.sh`
patch only has to set `android:debuggable="true"`. That flag activates the app's
own `<debug-overrides><certificates src="user"/>`, which is what lets a
user-installed CA (Bumper's) be trusted. The one other exception is a channel
that uses a **native mbedTLS stack** (`jmq-ngiot-*.ecouser.net`, Aliyun NGIoT):
native TLS reads the system CA store and ignores the user store, so a user CA
will not fix it. If one domain fails while everything else works, suspect this
before suspecting the SAN list.

**MQTT is the one real pin.** The Paho fork builds its `SSLSocketFactory` from a
certificate embedded in a `classes*.dex` and passes that KeyStore to
`TrustManagerFactory.init()`, which replaces the platform store entirely - no
user CA and no `<debug-overrides>` helps. `scripts/apk-patch/patch_mqtt_trust.py`
keeps a prefix of the embedded string so the dex `string_ids` table stays sorted,
which ART verifies, and makes `CertificateFactory` throw; the app's factory then
returns `null` and Paho falls back to the platform store. The dex carrying the
pin moves between app versions (`classes5.dex` in 3.15.1 as extracted locally,
`classes8.dex` in the same version as downloaded), so scan every `classes*.dex`.
`check_dex_strings.py` reproduces the sort check and `test_patch_mqtt_trust.py`
is a manual regression run - use it after changing either patcher.

**Consequence for TLS work:** widening `DOMAIN_SEC`/`certs.py` is a security
decision, not a compatibility one. Prefer adding the specific host over adding a
wildcard.

**The app's HTTP timeout is 15 s**, measured: successful calls return in
0.04-0.12 s and failures at exactly 15.0 s. `bumper/mqtt/helper_bot.py` waits
60 s for a robot, so an offline robot can never surface as an error to the app -
it always looks like a timeout. Changing that wait needs fidelity evidence.

**App-side problems are found in a device log, not in tests.** To check a change
against the real app, capture one symptom at a time:

```sh
adb logcat -c
# reproduce exactly one thing
adb logcat -d --pid=$(adb shell pidof -s com.eco.global.app) > app.log
```

The app logs every request and its outcome as `<-- <status> <url>`, so a tally
grouped by path finds the endpoints Bumper does not serve:

```sh
grep -oE '<-- [0-9]{3} [A-Za-z ]+ https://[^ ]*' app.log \
  | sed -E 's#(<-- [0-9]+) [A-Za-z ]+ https://[^/]+(/[^ ?]*).*#\1 \2#' | sort | uniq -c
```

A route that returns 404 in this tally is a real gap, and so is a call that is
missing from it entirely (the app gives up on the screen instead). Note which
host each call went to: the app uses more than one, for example both
`codepush-base.dc-na.ww.ecouser.net` and `codepush-base.ecouser.net`.

**The map of a job is a grid, and the picture of it has rules.** The robot
uploads the map of a finished job to the data-collect endpoint as a JSON
document. `minorMap.value` is the grid, one byte per cell, compressed with the
"7z" format - which is the LZMA "alone" format with a four byte size instead
of an eight byte one (`bumper/utils/map_doc.py` decodes it).

- The grid is `pieceWidth` by `pieceHeight` pieces of `cellWidth` by
  `cellHeight` cells, so 800 by 800 cells for the usual robot.
- Every cell holds an **index into the palette of the map**: 0 transparent, 1
  floor, 2 wall, 3 carpet, 4 not scanned space, 5 possible obstacle, and 6 and
  up are the rooms. Newer robots give every room a number of its own, so a room
  is drawn with the colour `(value % 6) + 6`.
- The picture of the map is the grid **turned a quarter turn clockwise**, the
  same way the app and the Home Assistant client draw it
  (`bumper/utils/map_image.py`, which was verified against the picture the
  `DeebotUniverse/client.py` Rust code produces).
- `majorMap.value` is the checksum of every piece. The value `1295764014` is
  the checksum of an empty piece and means **the robot has no map for that
  piece** - it does not mean the piece is empty.
- The app asks for the map of a job with `lg/log.do` and `td: "GetCleanedMap"`
  and expects the pieces of the grid and the driven path, both compressed the
  same way, keyed by the piece number and the trace id. The work log screen
  uses `/app/dln/api/log/clean_result/list` instead, and the picture of the
  job comes from the `imageUrl` of the entry, which has to point at the map
  that is stored here.

## Repository layout

```
bumper/          the Python package (web, mqtt, xmpp, db, utils)
  web/plugins/   auto-discovered Ecovacs API endpoint handlers
  web/static_api/  pre-fetched JSON served offline; see docs/development/static-data-update.md
docs/            mkdocs-material site, published via mkdocs-release.yml
scripts/         maintainer helper scripts (ruff-exempt, not shipped in the image)
  apk-patch/    the app patchers + their Docker image; see docs/internals/certificate-unpinning-app.md
configs/         nginx + mitmproxy configs used with the compose files
tests/           mirrors bumper/
.github/         CI, CodeQL, Docker + docs publishing, Renovate, Release Drafter,
                 and the issue/PR/discussion templates; see GitHub automation above
```

`bumper/web/static_api/` is generated data, not hand-edited. Regenerate via the
`scripts/update-eco-*.sh` flow documented in
`docs/development/static-data-update.md`; several of those files need real
Ecovacs credentials, so they cannot be refreshed in an automated environment.

## Commit and PR conventions

- Conventional Commits, as in existing history: `feat(core):`, `fix(deps):`,
  `chore(config):`, `docs:`, `test(tests):`, `refactor(core):`.
- PRs target `main`. `main` and `dev` are both in active development and may be
  unstable.
- **`.gitignore` is an allowlist**: it ignores `*` and then re-includes known
  paths. Any new top-level file must be explicitly re-included or it will be
  invisible to git.

`.github/PULL_REQUEST_TEMPLATE.md` asks for a summary, a `Fixes #issue` line, a
manual "Type of change" checkbox group (bug fix / feature / breaking / docs),
how it was tested, and the usual checklist. Note that those checkboxes are
informational only - they do **not** drive the release. Labels do (see below).

## GitHub automation

Release notes and the version bump are driven by **labels, not by commit types**.
Release Drafter (`.github/release-drafter.yml`) declares its whole config
inline - categories, template, and version resolver. What matters:

- `include-labels` is `pr: Breaking Change`, `pr: enhancement`,
  `pr: dependency-update`, `pr: new-feature`, `pr: bugfix`, `pr: refactor`,
  `pr: documentation`. A PR with **none** of these is silently dropped from the
  changelog, so it never reaches a user.
- `version-resolver` maps those labels to semver: `pr: Breaking Change` ->
  major; `pr: enhancement` / `dependency-update` / `new-feature` /
  `documentation` -> minor; `pr: bugfix` -> patch; anything unmatched defaults
  to patch.
- Each label also has a matching `:emoji:` section in `categories`, so an
  unlabeled-but-included PR lands in `template: "$CHANGES"` with no heading.
- Tagging a commit `v*` is what triggers the release: the tag pushes to
  `release-drafter.yml`, which drafts the GitHub release. Do not hand-write
  `CHANGELOG.md` or bump `version` in `pyproject.toml` - neither is wired to the
  release; `APP_VERSION` is read at runtime via `importlib.metadata`.

**Workflows** (`.github/workflows/`)

| Workflow              | Trigger                   | Notes                                                       |
| --------------------- | ------------------------- | ----------------------------------------------------------- |
| `ci.yml`              | push `main`/`dev`, any PR | prek + mypy/pylint, then pytest on Python 3.13 **and** 3.14 |
| `codeql-analysis.yml` | push `main`/`dev`, any PR | Python only                                                 |
| `docker-release.yml`  | push `dev`, tag `v*`      | Builds `linux/amd64` + `linux/arm64` to `ghcr.io`           |
| `mkdocs-release.yml`  | push `main`               | `mkdocs gh-deploy` to the `gh-pages` branch                 |
| `release-drafter.yml` | tag `v*`                  | Updates the release draft                                   |

Three things to know before changing CI or expecting a release:

- In `ci.yml`, `tests` has `needs: [prek, code-quality]`. A lint or type
  failure blocks the tests from starting at all, so a red test job often means a
  lint error further up the log.
- The test job uploads to Codecov with `fail_ci_if_error: true`. A Codecov
  outage fails CI even when every test passed - check that before debugging.
- **The Docker image is published from `dev`, not `main`** - the `main` trigger
  is commented out in `docker-release.yml`, while docs publish from `main`.
  Cutting a release therefore means pushing `v*`, not merging to `main`.

**Renovate** (`.github/renovate.json`) is the only dependency bot (there is no
Dependabot config). `lockFileMaintenance` is on, the dependency dashboard is off,
and `automerge: false` on every group - dependency PRs need a human merge.
Python deps group into "Python dependencies" and "Python development
dependencies"; GitHub Actions, Dockerfile, and pre-commit hooks each pin with
`rangeStrategy: "pin"` and get their own group. `"pre-commit": {"enabled": true}`
means hook `rev:` values in `.pre-commit-config.yaml` are bumped automatically -
keep them in sync with the local hook versions rather than editing them
independently.

**Issues.** `blank_issues_enabled: false`, and `ISSUE_TEMPLATE/config.yml`
routes everything that is not a bug away from the tracker: questions to
Discussions, feature requests to the Discussions feature-requests category, and
security reports to `github.com/MVladislav/bumper/security/advisories`. **Never
open a public issue for a vulnerability.** The bug form (`bug_report.yml`)
auto-applies the `bug` label and requires Docker version, host OS, robot model,
and Bumper version - ask for those specifics when triaging, and note the "Is the
bug related to" checkbox still reads `XAMPP` where it means XMPP.

Actions are pinned by version tag (`actions/checkout@v7.0.1`), not by SHA.
Renovate's pin strategy keeps the tags current; converting to SHA pinning is a
security decision to raise, not to do silently in a dependency PR.

## Docs

- User-facing docs live in `docs/` as mkdocs-material pages. Adding a page means
  adding it to the `nav:` in `mkdocs.yml` too.
- Docs use American spelling ("behavior", "license", "color"); match the existing
  text when editing.
- `docs/internals/architecture.md` is explicitly a work in progress; keep its
  disclaimer if you extend it.

## Risks

- **Protocol fidelity is the core asset.** A response shape that looks wrong but
  matches captured traffic is correct. Verify against real captured traffic
  before "fixing" anything.
- **Certificate trust is a security boundary.** Anything that widens what the
  generated CA is trusted for, or how the cert archive is served, needs explicit
  review.
- **Bot/app compatibility is empirical.** The supported device list in the README
  is based on user reports, not test coverage. Untested protocol changes can
  silently break models that no test covers.
- **Static data drifts.** Hand-maintained JSON in `web/static_api/` will
  disagree with the live Ecovacs API over time; don't assume it is current.
- **The database is not a real database.** TinyDB loads whole files; migrations
  back up before running, but large instances can be slow and memory-heavy.
