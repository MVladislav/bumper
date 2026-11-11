# ✨ Features

Bumper reimplements selected Ecovacs cloud features locally.
Availability depends on the robot model, firmware, app version, region, and whether required data files are present.

---

## 🗣️ Voice Languages {#voice-languages}

The official app can switch a robot's voice language.
Bumper serves the voice metadata the app requests and the voice file the robot downloads.

**What is needed**

- Voice metadata is part of Bumper's static data (`voices.json`).
- The actual voice files are not stored in the repository.
  Fetch metadata/files with the maintainer script described in
  [Static Data Update](../development/static-data-update.md)
  (`update-eco-voices.sh`).
- Place the downloaded files where Bumper can read them.
  By default that is `${BUMPER_DATA}/voices` (`BUMPER_VOICES` overrides the path).
  In Docker, put them in the data volume; see [Docker](docker.md).

**Behavior**

- Bumper serves voice metadata/language information to the app and serves voice files from `BUMPER_VOICES`.
- If a requested voice file is missing, Bumper logs a warning and returns `404` for that file.
  The robot keeps its current language instead of installing the new one.
- At startup Bumper logs how many voice files it found, for example:

    ```text
    INFO :: bumper.web.server - Voice files :: 13 in '/bumper/data/voices'
    ```

---

## 🗺️ Work Logs and Clean Maps

After a cleaning job, supported robots can upload job data and map data.
Bumper stores that data and serves it back to the app and its own web UI.

**In the official app**

- The work-log list is served by `/app/dln/api/log/clean_result/list` (for supported `logType=clean` requests).
- When a stored map exists for a job, Bumper provides an image URL for that job.

**In the Bumper web UI**

- Open **Clean Logs** and use a job's menu to choose **Show map**.
  The map is rendered and displayed over the page.

**Storage and limits**

- Uploaded pictures and cleaned maps are stored per robot.
  When the per-device limit is reached, older items are removed on new uploads.
  Configure with `PHOTO_MAX_PER_DEVICE`.
- Clean-log entries are stored per robot and pruned to `CLEAN_LOG_MAX_PER_DEVICE`.
- Support depends on what the robot/app uploads and requests.
  Not every model or app flow exposes the same history.

---

## 📱 App Updates (CodePush) {#app-updates-codepush}

The official app can load JavaScript bundles from CodePush instead of only using
the bundles shipped in the APK. Bumper answers the app's update check from its
static data (`updateCheck.json` and `updateCheck_mapping.json`).

**Serving packages locally**

- By default the update check points the app at the cloud for the package
  download. Set `CODEPUSH_LOCAL_PACKAGE=true` to make Bumper answer with its
  own download URL:
  `https://<codepush-base host>/api/appsvr/codepush/download/<deployment_key>`.
  That host is covered by the wildcard DNS override.
- The package files have to be in `${BUMPER_DATA}/codepush`
  (`BUMPER_CODEPUSH` overrides the path) and are named after their deployment
  key. `scripts/data/3-update-eco-codepush-packages.sh` writes them there.
  See [Docker: Extra data files](docker.md#extra-data-files-voices-codepush)
  for copying them into a container or Swarm node.
- If a package is missing, the download answers `404` and the app keeps its
  current bundle.
- The packages are large and are not part of the image or repository.
  Refresh them with the script above; see
  [Static Data Update](../development/static-data-update.md).

!!! warning "CodePush ships app logic"

    A CodePush bundle is executable app code, not just an image or a translation
    file. A stale or mismatched `updateCheck.json` entry can make the app behave
    incorrectly. Keep the metadata and the packages in sync with the app version
    you are running.

---

## ⚙️ Related configuration

`BUMPER_VOICES`, `BUMPER_CODEPUSH`, `CODEPUSH_LOCAL_PACKAGE`,
`PHOTO_MAX_PER_DEVICE`, and `CLEAN_LOG_MAX_PER_DEVICE` change this page's
behavior; each is described in
[Environment Variables](../configuration/environment.md). The data files are
refreshed with the scripts in [Static Data Update](../development/static-data-update.md).
