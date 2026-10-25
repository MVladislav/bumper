#!/usr/bin/env bash
# Shared path helpers for the scripts.
#
# The scripts write into the repository and into the data directory, so their
# paths have to be absolute: a relative path resolves against the directory the
# script happens to run in.
#
# NOTE: lint with 'shellcheck -x <script>' (follows the sourced file)

# The directory of this file, and with it the root of the repository: the
# helpers live in scripts/shared, so the root is two levels up. The scripts
# live in scripts/<folder>, so the root is the same for all of them.
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC2034
REPO_ROOT="$(cd "$SHARED_DIR/../.." && pwd -P)"

# Print the absolute form of a path. A relative path is taken against the
# current directory.
abspath() {
  case "$1" in
  /*) printf '%s' "$1" ;;
  *) printf '%s/%s' "$PWD" "$1" ;;
  esac
}
