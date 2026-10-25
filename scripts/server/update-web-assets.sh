#!/usr/bin/env bash
set -eu

# Fetch the latest version of htmx from its npm registry
VERSION_HTMX=$(curl -sSfL "https://registry.npmjs.org/htmx.org" | jq -r '.["dist-tags"].next')
# Fetch the latest version of Bootstrap from its CDN
VERSION_BOOTSTRAP=$(curl -sSfL "https://api.cdnjs.com/libraries/bootstrap" | jq -r '.version')

# Download the latest versions
echo "Update latest version for htmx as '${VERSION_HTMX}' ..."
curl -sSfL "https://unpkg.com/htmx.org@${VERSION_HTMX}/dist/htmx.min.js" -o "bumper/web/static_web/js/htmx.min.js"
echo "Update latest version for bootstrap as '${VERSION_BOOTSTRAP}' ..."
curl -sSfL "https://cdn.jsdelivr.net/npm/bootstrap@${VERSION_BOOTSTRAP}/dist/css/bootstrap.min.css" -o "bumper/web/static_web/css/bootstrap.min.css"
