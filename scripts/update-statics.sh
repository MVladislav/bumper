#!/usr/bin/env bash
set -eu

# Fetch the latest version of htmx from its npm registry
VERSION_HTMX=$(curl -s "https://registry.npmjs.org/htmx.org" | jq -r '.["dist-tags"].next')

# Fetch the latest version of Bootstrap from its CDN
VERSION_BOOTSTRAP=$(curl -s "https://api.cdnjs.com/libraries/bootstrap" | jq -r '.version')

# Download the latest versions
curl -L "https://unpkg.com/htmx.org@${VERSION_HTMX}/dist/htmx.min.js" -o "bumper/web/static_web/js/htmx.min.js"
curl -L "https://cdn.jsdelivr.net/npm/bootstrap@${VERSION_BOOTSTRAP}/dist/css/bootstrap.min.css" -o "bumper/web/static_web/css/bootstrap.min.css"
