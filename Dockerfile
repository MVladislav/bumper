# syntax=docker/dockerfile:1

# https://hub.docker.com/_/python/tags
ARG PY_VERSION=3.15-alpine3.23
# https://github.com/astral-sh/uv/pkgs/container/uv
ARG UV_VERSION=python3.15-alpine3.23

# ------------------------------------------------------------------------------

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv_source
FROM python:${PY_VERSION} AS builder

COPY --from=uv_source /usr/local/bin/uv /usr/local/bin/uv

WORKDIR /bumper
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev --no-install-project

COPY bumper ./bumper
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --locked --no-dev --no-editable

# ------------------------------------------------------------------------------

FROM python:${PY_VERSION}

# The release workflow passes these; a plain local build keeps the defaults.
ARG VERSION=
ARG BUILDTIME
ARG REVISION

LABEL org.opencontainers.image.source=https://github.com/MVladislav/bumper
LABEL org.opencontainers.image.description="bumper"
LABEL org.opencontainers.image.licenses=GPLv3
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.created=$BUILDTIME
LABEL org.opencontainers.image.revision=$REVISION

# The app reports this version in the UI and uses it for the database version.
ENV VERSION_BUMPER=$VERSION
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /bumper

RUN apk add --no-cache su-exec \
  && addgroup -S -g 1000 bumper \
  && adduser -S -u 1000 -G bumper bumper \
  && mkdir -p data certs \
  && chown -R bumper:bumper /bumper

COPY --from=builder --chown=bumper:bumper /bumper/.venv /bumper/.venv

# Volumes created by an image that ran as root are owned by root, so repair the
# ownership of the writable directories before dropping privileges. Without
# this an upgraded install cannot write its database.
COPY <<'ENTRYPOINT' /usr/local/bin/docker-entrypoint.sh
#!/bin/sh
set -eu

if [ "$(id -u)" != "0" ]; then
  exec "$@"
fi

data="${BUMPER_DATA:-/bumper/data}"
certs="${BUMPER_CERTS:-/bumper/certs}"

for dir in "$data" "$certs"; do
  if [ -d "$dir" ] && [ "$(stat -c %u "$dir")" != "1000" ]; then
    chown -R bumper:bumper "$dir" 2>/dev/null || true
  fi
done

for dir in "$data" "$certs"; do
  if [ -d "$dir" ] && [ "$(stat -c %u "$dir")" != "1000" ]; then
    echo "bumper: $dir is owned by $(stat -c %u:%g "$dir") and cannot be changed." >&2
    echo "bumper: grant the CHOWN capability or run 'chown -R 1000:1000' on it." >&2
    exit 1
  fi
done

exec su-exec bumper "$@"
ENTRYPOINT

RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/bumper/.venv/bin/bumper"]

EXPOSE 443 8007 8883 1883 5223
