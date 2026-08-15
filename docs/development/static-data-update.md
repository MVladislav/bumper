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

---

## 🔄 Scripts

| Script                           | Needs login                         | Reads                 | Writes                                                                         |
| -------------------------------- | ----------------------------------- | --------------------- | ------------------------------------------------------------------------------ |
| `update-eco-data.sh`             | ✅ (password + optional email code) | Ecovacs private API   | `configGroupsResponse.json`, `configNetAllResponse.json`, `productIotMap.json` |
| `update-eco-codepush.sh`         | ❌                                  | `codePushConfig.json` | `updateCheck.json`                                                             |
| `update-eco-codepush-mapping.sh` | ❌                                  | `updateCheck.json`    | `updateCheck_mapping.json`                                                     |

Run them in this order, as each script needs the previous one's output:

1. **`scripts/update-eco-data.sh`** — logs in to the Ecovacs private API and
   downloads the per-country product configs (`DE`, `US`, other countries from
   `COUNTRIES`), combines them with the committed files and rewrites the
   download URLs to local domains (see [combination rules](#combination-rules)).
2. **`scripts/update-eco-codepush.sh`** — queries the public codepush
   `update_check` endpoint for every deployment key in `codePushConfig.json`
   and combines the results into `updateCheck.json`. Download URLs are stripped
   of their AWS signing parameters. Downloads run in parallel (`ECO_PARALLEL`).
3. **`scripts/update-eco-codepush-mapping.sh`** — downloads the codepush
   bundles referenced by `updateCheck.json`, extracts the main folder of each
   bundle and writes the `{main_folder: deployment_key}` mapping used by the
   app (see `appsvr.py` `get_codepush_update_check_data`).

All scripts write their per-run artefacts to `json_mappings/` (gitignored) and
copy the final files into `bumper/web/static_api/`. All outputs are sorted, so
re-runs produce stable diffs.

---

## 🚀 Usage

**Step 1 – Refresh the product data** (needs an Ecovacs account):

```sh
$ ECOVACS_ACCOUNT_ID=your@email.com ECOVACS_PASSWORD=your_password scripts/update-eco-data.sh
```

On the first login from a new device, Ecovacs answers with error `1013` and the
script triggers a device verification: a code is emailed to the account address
and you are prompted for it. Provide it upfront to skip the prompt:

```sh
$ ECO_VERIFY_CODE=123456 scripts/update-eco-data.sh
```

> **Note:** verification codes are single-use and repeated requests are
> rate-limited by Ecovacs (`0002 "Parameter error. Please try again later."`).
> Wait 10–30 minutes before retrying.

Verification is bound to the device id stored in `.eco-device-id` (gitignored),
so subsequent runs log in directly without a code.

**Step 2 – Refresh the codepush data** (no login needed):

```sh
$ scripts/update-eco-codepush.sh
$ scripts/update-eco-codepush-mapping.sh
```

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

| Variable                                 | Used by                                                    | Purpose                                                                   |
| ---------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| `ECOVACS_ACCOUNT_ID`, `ECOVACS_PASSWORD` | `update-eco-data.sh`                                       | Ecovacs account credentials (required)                                    |
| `ECO_DEVICE_ID`                          | `update-eco-data.sh`                                       | Stable device id (default: generated once and stored in `.eco-device-id`) |
| `ECO_DEVICE_ID_FILE`                     | `update-eco-data.sh`                                       | Custom path for the device id file                                        |
| `ECO_VERIFY_CODE`                        | `update-eco-data.sh`                                       | Skip the prompt with a pre-fetched email verification code                |
| `ECO_CHANNEL`                            | `update-eco-data.sh`                                       | App channel (`google_play` default; `google` worked in some regions)      |
| `ECO_PARALLEL`                           | `update-eco-codepush.sh`, `update-eco-codepush-mapping.sh` | Number of parallel downloads (default `4`)                                |
