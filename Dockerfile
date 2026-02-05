# https://hub.docker.com/_/python/tags
ARG PY_VERSION=3.14.3-alpine3.22
# https://github.com/astral-sh/uv/pkgs/container/uv
ARG UV_VERSION=python3.14-alpine

# ------------------------------------------------------------------------------

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv_source
FROM python:${PY_VERSION} AS builder
# COPY --from=ghcr.io/astral-sh/uv:python3.14-alpine /uv /uvx /bin/
COPY --from=uv_source /usr/local/bin/uv /usr/local/bin/uvx /bin/

RUN apk add --no-cache \
  bash \
  git \
  openssl \
  gcc \
  musl-dev \
  linux-headers

WORKDIR /bumper
COPY . .
RUN uv sync --no-dev --no-editable --no-cache

# ------------------------------------------------------------------------------

FROM python:${PY_VERSION}

LABEL org.opencontainers.image.source=https://github.com/MVladislav/bumper
LABEL org.opencontainers.image.description="bumper"
LABEL org.opencontainers.image.licenses=GPLv3

RUN addgroup -S -g 1000 bumper && adduser -S -u 1000 -G bumper bumper
COPY --from=builder --chown=bumper:bumper /bumper/.venv /bumper/.venv

# RUN chown -R bumper:bumper /bumper
# USER bumper

WORKDIR /bumper
CMD ["/bumper/.venv/bin/bumper"]
