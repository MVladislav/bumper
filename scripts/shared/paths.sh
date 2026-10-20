#!/usr/bin/env bash
# Shared path helpers for the update-eco-*.sh scripts.
#
# The scripts write into the repository and into the data directory, so their
# paths have to be absolute: a relative path resolves against the directory the
# script happens to run in.
#
# NOTE: lint with 'shellcheck -x <script>' (follows the sourced file)

# The root of the repository, derived from the location of the script. The
# scripts set SCRIPT_DIR before sourcing this file.
# shellcheck disable=SC2034
REPO_ROOT="$(cd "${SCRIPT_DIR:-$(pwd)}/.." && pwd -P)"

# Print the absolute form of a path. A relative path is taken against the
# current directory.
abspath() {
  case "$1" in
  /*) printf '%s' "$1" ;;
  *) printf '%s/%s' "$PWD" "$1" ;;
  esac
}
