# Static Data Update Guide

Bumper serves some data from pre-fetched files under `bumper/web/static_api/`
instead of querying the Ecovacs cloud, so the app keeps working fully offline.
This data changes over time; this guide explains which files exist and how to
refresh them with the helper scripts in `scripts/`.

> **Note:** the process is not fully automatable. `update-eco-data.sh` requires
> an Ecovacs account login, and the first login from a new device may require
> an email verification code. The scripts are meant to be run manually by a
> maintainer.

---

## 📦 What Gets Updated

All files live in `bumper/web/static_api/` and are served to the app from
Bumper's own web server instead of the Ecovacs cloud:

| File                        | Served to the app at                     | What it contains                                                                             |
| --------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------- |
| `configGroupsResponse.json` | `POST /product/getConfigGroups`          | Product groups with their robot models and Wi-Fi setup steps (product configuration screens) |
| `configNetAllResponse.json` | `POST /product/getConfignetAll`          | All robot models with their Wi-Fi setup steps (`steps`, `customSteps`)                       |
| `productIotMap.json`        | `POST /product/getProductIotMap`         | `classid` → product info (QR-code decoding, bot list enrichment)                             |
| `updateCheck.json`          | `GET /v0.1/public/codepush/update_check` | `deployment_key` → latest bundle info (`download_url`, `is_available`, `is_mandatory`, …)    |
| `updateCheck_mapping.json`  | (lookup for the codepush update check)   | `main_folder` → `deployment_key`, resolves update checks sent by package name                |
| `timezones.json`            | `GET /basis/time/timezones`              | The time zones of the app, with their name in every language                                 |
| `voices.json`               | `GET /pim/voice/get`                     | The voice of every language the app offers, with the file the robot has to download          |

---

## 🔄 Scripts

| Script                              | Needs login                         | Reads                 | Writes                                                                         |
| ----------------------------------- | ----------------------------------- | --------------------- | ------------------------------------------------------------------------------ |
| `update-eco-data.sh`                | ✅ (password + optional email code) | Ecovacs private API   | `configGroupsResponse.json`, `configNetAllResponse.json`, `productIotMap.json` |
| `1-update-eco-codepush.sh`          | ❌                                  | `codePushConfig.json` | `updateCheck.json`                                                             |
| `2-update-eco-codepush-mapping.sh`  | ❌                                  | `updateCheck.json`    | `updateCheck_mapping.json`                                                     |
| `3-update-eco-codepush-packages.sh` | ❌                                  | `updateCheck.json`    | the CodePush packages in the CodePush directory                                |
| `update-eco-timezones.sh`           | ✅ (password + optional email code) | Ecovacs api base      | `timezones.json`                                                               |
| `update-eco-voices.sh`              | ✅ (password + optional email code) | Ecovacs portal API    | `voices.json` and the voice files in the voice directory                       |

Most of the scripts are maintenance: they refresh the information Bumper
serves, and the result is pushed into the repository. Run them when that
information has to be brought up to date.

Two of them fetch files that are large and that stay out of the repository -
the voice files and the CodePush packages. They are only needed when those
files are to be served from Bumper instead of from the cloud.

The three CodePush scripts carry a prefix that matches their order inside the
group. Run the scripts in this order when you refresh everything. Inside the
CodePush group each script needs the output of the previous one; the other
scripts are independent.

1. **`scripts/data/update-eco-data.sh`** - logs in to the Ecovacs private API and
   downloads the per-country product configs (`DE`, `US`, other countries from
   `COUNTRIES`), combines them with the committed files and rewrites the
   download URLs to local domains (see [combination rules](#combination-rules)).
2. **`scripts/data/1-update-eco-codepush.sh`** - queries the public codepush
   `update_check` endpoint for every deployment key in `codePushConfig.json`
   and combines the results into `updateCheck.json`. Download URLs are stripped
   of their AWS signing parameters. Downloads run in parallel (`ECO_PARALLEL`).
3. **`scripts/data/2-update-eco-codepush-mapping.sh`** - downloads the codepush
   bundles referenced by `updateCheck.json`, extracts the main folder of each
   bundle and writes the `{main_folder: deployment_key}` mapping used by the
   app (see `appsvr.py` `get_codepush_update_check_data`).
4. **`scripts/data/3-update-eco-codepush-packages.sh`** - downloads the CodePush
   packages of the deployments, so that the app can update without reaching
   the cloud. Only needed when the packages are to be served from Bumper
   (`CODEPUSH_LOCAL_PACKAGE`). The packages are a few MB to a few dozen MB
   each and are **not** part of the repository: they land in the CodePush
   directory (`BUMPER_CODEPUSH`, `${BUMPER_DATA}/codepush` by default). The
   script needs no login, but it needs the urls of `updateCheck.json`, so it
   runs after `1-update-eco-codepush.sh`. Downloads run in parallel (`ECO_PARALLEL`).
5. **`scripts/data/update-eco-timezones.sh`** - fetches the time zones the app shows,
   with their name in every language, and writes them to `timezones.json`.
6. **`scripts/data/update-eco-voices.sh`** - fetches the voice of every language the
   app offers and writes the metadata to `voices.json`. Only needed when the
   robot is to change its voice language. The voice files themselves are a
   few MB each and are **not** part of the repository: they land in the voice
   directory (`BUMPER_VOICES`, `${BUMPER_DATA}/voices` by default) and have to
   be present before the server starts.

All scripts write their per-run artefacts to `json_mappings/` (gitignored) and
copy the final files into `bumper/web/static_api/`. All outputs are sorted, so
re-runs produce stable diffs.

> **Note:** run the scripts **before the DNS override is in place**, or from a
> machine that can still reach the Ecovacs cloud - the override points the
> cloud names at Bumper.

> **Note:** the voice files and the CodePush packages are the exceptions to
> "everything ends up in `static_api/`". They are large and they are fetched
> from the cloud, so they are kept out of the repository on purpose.

---

## 🚀 Usage

**Step 1 - Refresh the product data** (needs an Ecovacs account):

```sh
ECOVACS_ACCOUNT_ID=your@email.com ECOVACS_PASSWORD=your_password scripts/data/update-eco-data.sh
```

On the first login from a new device, Ecovacs answers with error `1013` and the
script triggers a device verification: a code is emailed to the account address
and you are prompted for it.

> **Note:** verification codes are single-use and repeated requests are
> rate-limited by Ecovacs (`0002 "Parameter error. Please try again later."`).
> Wait 10-30 minutes before retrying.
>
> > Verification is bound to the device id stored in `.eco-device-id` (gitignored),
> > so subsequent runs log in directly without a code.

**Step 2 - Refresh the codepush data** (no login needed):

```sh
scripts/data/1-update-eco-codepush.sh
scripts/data/2-update-eco-codepush-mapping.sh
```

**Step 3 - Download the CodePush packages** (no login needed):

```sh
scripts/data/3-update-eco-codepush-packages.sh
```

Only needed when the packages are to be served from Bumper
(`CODEPUSH_LOCAL_PACKAGE=true`). The script downloads the package of every
deployment of `updateCheck.json`, at the same time. The packages are large, so
the deployments to fetch can be named:

```sh
CODEPUSH_DEPLOYMENT_KEYS=<the deployment key> scripts/data/3-update-eco-codepush-packages.sh
```

The files are written to `${BUMPER_DATA}/codepush` unless `BUMPER_CODEPUSH`
says otherwise. In a container the data directory is a volume, so the packages
either live in that volume or are copied into it:

```sh
docker cp ./data/codepush/. <container>:/bumper/data/codepush/
```

**Step 4 - Refresh the time zones** (needs an Ecovacs account):

```sh
ECOVACS_ACCOUNT_ID=your@email.com ECOVACS_PASSWORD=your_password scripts/data/update-eco-timezones.sh
```

The time zones are the same for every user, but the api wants a login. The host
of the api belongs to the region of the account, `API_BASE_HOST` sets it.

**Step 5 - Refresh the voice files** (needs an Ecovacs account):

```sh
ECOVACS_ACCOUNT_ID=your@email.com ECOVACS_PASSWORD=your_password scripts/data/update-eco-voices.sh
```

Only needed when the robot is to change its voice language.

> **Note:** verification codes are single-use and repeated requests are
> rate-limited by Ecovacs (`0002 "Parameter error. Please try again later."`).
> Wait 10-30 minutes before retrying.
>
> > Verification is bound to the device id stored in `.eco-device-id` (gitignored),
> > so subsequent runs log in directly without a code.

The files are written to `${BUMPER_DATA}/voices` unless `BUMPER_VOICES` says
otherwise, and the metadata to `bumper/web/static_api/voices.json`.

In a container the data directory is a volume, so the files either live in
that volume or are copied into it:

```sh
docker cp ./data/voices/. <container>:/bumper/data/voices/
```

The app downloads the package from the cloud unless `CODEPUSH_DOWNLOAD_HOST`
names the host that answers for Bumper:

```sh
CODEPUSH_DOWNLOAD_HOST=codepush-base.ecouser.net
```

With that set, the update check answers with the url of the package on that
host, and the app downloads it from Bumper instead of from the cloud. The host
has to be one that the DNS override points at Bumper.

---

## 🔀 Combination Rules

`update-eco-data.sh` combines the per-country responses with the currently
committed files:

- **Country priority:** each entry (by `id` / `groupId` / `classid`) is taken
  from `DE` if present, otherwise `US`, otherwise any other country; entries
  that no country supplies anymore are kept from the committed file.
- **Consistency:** object keys are sorted recursively, so key reordering in
  upstream responses does not produce noisy diffs between runs.
- **Robustness:** countries whose request failed are skipped instead of
  poisoning the combination.

---

## ⚙️ Environment Variables

| Variable                                 | Used by                                                        | Purpose                                                                   |
| ---------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `ECOVACS_ACCOUNT_ID`, `ECOVACS_PASSWORD` | `update-eco-data.sh`, `update-eco-voices.sh`                   | Ecovacs account credentials (required)                                    |
| `ECO_DEVICE_ID`                          | `update-eco-data.sh`, `update-eco-voices.sh`                   | Stable device id (default: generated once and stored in `.eco-device-id`) |
| `ECO_DEVICE_ID_FILE`                     | `update-eco-data.sh`, `update-eco-voices.sh`                   | Custom path for the device id file                                        |
| `ECO_VERIFY_CODE`                        | `update-eco-data.sh`, `update-eco-voices.sh`                   | Skip the prompt with a pre-fetched email verification code                |
| `ECO_CHANNEL`                            | `update-eco-data.sh`                                           | App channel (`google_play` default; `google` worked in some regions)      |
| `ECO_PARALLEL`                           | `1-update-eco-codepush.sh`, `2-update-eco-codepush-mapping.sh` | Number of parallel downloads (default `4`)                                |
| `BUMPER_VOICES`                          | `update-eco-voices.sh`                                         | Where the voice files are written (default: `${BUMPER_DATA}/voices`)      |
| `VOICE_LANGS`                            | `update-eco-voices.sh`                                         | The languages to fetch, comma separated (default: every language)         |
| `API_BASE_HOST`                          | `update-eco-timezones.sh`                                      | The api host of the region (default: `api-base.dc-eu.ww.ecouser.net`)     |
