# The maintainer scripts

These are the tools of the repository. They are not part of the image and
they are not run by the server - they are run by a maintainer, by hand, when
something has to be refreshed, checked or patched.

Every script is in the folder of what it is for:

| Folder           | What is in it                                                            |
| ---------------- | ------------------------------------------------------------------------ |
| `api/`           | The tools that read or check the API                                     |
| `app/`           | The script to unpin the apk app to work with the bumper self signed cert |
| `app/apk-patch/` | The patchers of the app, which are used inside the scripts               |
| `certs/`         | The certificate creator script                                           |
| `data/`          | The scripts that update the static data needed for the bumper api        |
| `server/`        | The scripts that update the used server resources                        |
| `shared/`        | The helpers the other scripts use                                        |

## The tools of the API

| Script                                    | What it does                                                                                               | Do you need it?                                                   |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `api/api-table.py`                        | Prints the route table with the shape of every endpoint                                                    | When you want to see what the server serves                       |
| `api/1-convert-mitmproxy-flows-export.py` | Turns mitmproxy flows into transcripts, including complete decoded MQTT streams even on TLS port 443       | When you have a new recording to inspect                          |
| `api/2-extract-response-shapes.py`        | Writes the shape of every captured answer into the two files under `tests/web/`                            | When the traffic has grown and the shapes are to be checked again |
| `api/check-captured-apis.py`              | Compares the route table with the captured traffic: what does the app call that the server does not serve? | When you look for a gap in the API                                |
| `api/sync-route-snapshots.py`             | Writes `tests/web/routes.txt` and `tests/web/shapes.txt` from the live route table                         | When an endpoint or its answer shape changes                      |
| `api/check-eco-firmware.sh`               | Checks the firmware of a robot against the one the cloud offers                                            | When a robot does not get the update it should                    |

The converter and the extractor are numbered because the extractor reads what
the converter writes. `check-captured-apis.py` is an optional diagnostic and
can run after step 1.

`2-extract-response-shapes.py` writes `tests/web/response_shapes.json` and
`tests/web/response_shapes_bumper.json` - the fixtures that
`tests/web/test_response_shapes.py` checks the server against in CI.
`sync-route-snapshots.py` writes the route and shape snapshots that
`tests/web/test_routes.py` and `tests/web/test_shapes.py` pin. The pre-commit
hook runs it when a file under `bumper/web/` changes; a snapshot change is
then part of the same commit.

### From a recording to the fixtures

The transcripts are local working data. They live in `data/flows/`, which is
git-ignored, and are made from an exported mitmproxy flow file:

```sh
# 1. write data/flows/<name>-clean
uv run --active --frozen python scripts/api/1-convert-mitmproxy-flows-export.py capture.mitm

# optional: see what the app called that the server does not answer
uv run --active --frozen python scripts/api/check-captured-apis.py

# 2. refresh the response-shape fixtures
uv run --active --frozen python scripts/api/2-extract-response-shapes.py
```

The converter keeps the input name, so name the input with one of the
prefixes the extractor reads: `flows_official_*` and `flows_new_*` for answers
of the official server, `flows-bumper-*` for answers of this server. `-o`
chooses a different output path, and `-o -` writes to stdout.

## The data the API answers with

These are the scripts that refresh `bumper/web/static_api/`. The CodePush
group has an order; the other scripts are independent. The whole flow is
documented in `docs/development/static-data-update.md`.

| Script                                   | What it does                                                             | Do you need it?                                    |
| ---------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------- |
| `data/update-eco-data.sh`                | Fetches the product configs (the robots, their setup steps)              | When the products of the shop change               |
| `data/1-update-eco-codepush.sh`          | Fetches the CodePush bundles of every deployment                         | When the app starts to update                      |
| `data/2-update-eco-codepush-mapping.sh`  | Maps the CodePush bundles to the deployments the app asks for            | With `1-update-eco-codepush.sh`                    |
| `data/3-update-eco-codepush-packages.sh` | Downloads the CodePush packages, so the app can update without the cloud | Only if the app should update without the cloud    |
| `data/update-eco-timezones.sh`           | Fetches the time zones the app shows                                     | When a time zone is missing or wrong               |
| `data/update-eco-voices.sh`              | Fetches the voice files the robot downloads                              | Only if the robot should change its voice language |

The three CodePush scripts are numbered because they run in order: 1 writes
`updateCheck.json`, 2 maps it, and 3 downloads the packages it names.

The scripts that need an account (`update-eco-data.sh`, `update-eco-timezones.sh`
and `update-eco-voices.sh`) ask for the credentials in the environment:

```sh
ECOVACS_ACCOUNT_ID=your@email.com ECOVACS_PASSWORD=your_password scripts/data/update-eco-voices.sh
```

The two that fetch the CodePush packages and the voices write their files
**outside** the repository (into `BUMPER_CODEPUSH` and `BUMPER_VOICES`), so
they have to be run again after a fresh checkout.

## The app

| Script                              | What it does                                                   | Do you need it?                          |
| ----------------------------------- | -------------------------------------------------------------- | ---------------------------------------- |
| `app/create-unpinned-app.sh`        | Patches the app so that it trusts a user-installed certificate | When you set up a phone for Bumper       |
| `app/create-unpinned-app-legacy.sh` | The same, for the older layout of the apk                      | Only for an old apk                      |
| `app/apk-patch/*`                   | The patchers themselves and the image that builds them         | Only when the pinning of the app changes |

The unpatched apks are in `data/` and are not committed.

## The certificates and the server

| Script                        | What it does                                         | Do you need it?                            |
| ----------------------------- | ---------------------------------------------------- | ------------------------------------------ |
| `certs/create-cert.sh`        | Creates the CA and the certificate of the server     | Once per installation                      |
| `certs/cert-san-domains.py`   | Prints the domains the certificate has to cover      | When the domains of the app change         |
| `server/update-web-assets.sh` | Refreshes the htmx and bootstrap files of the web ui | When the web ui should follow the upstream |

## Running them

The scripts that need Python run in the virtual environment of the
repository:

```sh
uv run --active --frozen python scripts/api/api-table.py
```

The shell scripts need `curl`, `jq` and sometimes `openssl`.
