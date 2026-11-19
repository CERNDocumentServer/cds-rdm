# Dockerfile that builds a fully functional image of your app.
#
# This image installs all Python dependencies for your application. It's based
# on the Invenio Debian image that ships Python 3.14, uv and Node.js
# (https://github.com/inveniosoftware/docker-invenio)
# and installs the few standard libraries Invenio usually needs.
#
# Note: It is important to keep the commands in this file in sync with your
# bootstrap script located in ./scripts/bootstrap.

ARG BUILD_PLATFORM=linux/amd64
ARG PNPM_VERSION=10.33.2

# --- Build stage ---
FROM --platform=${BUILD_PLATFORM} registry.cern.ch/inveniosoftware/debian:3.14 AS builder

# System libraries:
#  - libkrb5-dev / krb5-user: gssapi and requests-kerberos (build + Kerberos auth)
#  - libcairo2 / libmagickwand-7.q16-10: cairocffi and wand open these through ctypes,
#    so they are needed when the app is imported during `invenio collect/webpack`
#  - XRootD needs nothing here, the PyPI wheel (xrootd extra) bundles its libraries
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        krb5-user \
        libcairo2 \
        libgssapi-krb5-2 \
        libkrb5-dev \
        libmagickwand-7.q16-10 \
        pkg-config
# Kerberos configuration (requests-kerberos / XRootD auth)
COPY ./krb5.conf /etc/krb5.conf

ARG PNPM_VERSION
RUN npm install --global pnpm@${PNPM_VERSION}
ENV PNPM_STORE_DIR=/opt/.cache/pnpm-store

# Sits above project-source COPYs so the layer only invalidates when the lockfile
# changes. --shamefully-hoist must match the flag pynpm.PNPMPackage forces during the
# later `invenio webpack install`, otherwise that step would purge node_modules and
# reinstall from scratch.
RUN mkdir -p ${INVENIO_INSTANCE_PATH}/assets
COPY package.json pnpm-lock.yaml ${INVENIO_INSTANCE_PATH}/assets/
RUN --mount=type=cache,target=/opt/.cache/pnpm-store \
    cd ${INVENIO_INSTANCE_PATH}/assets && \
    pnpm install --frozen-lockfile --shamefully-hoist

# Python and uv configuration
# The base image ships Python 3.14; pin uv to it so it never picks another interpreter.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON=3.14 \
    UV_CACHE_DIR=/opt/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    UV_REQUIRE_HASHES=1 \
    UV_VERIFY_HASHES=1

# Install Python dependencies using uv
ARG BUILD_EXTRAS="--extra sentry --extra xrootd"
RUN --mount=type=cache,target=/opt/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --no-install-workspace --no-editable $BUILD_EXTRAS

COPY site ./site

COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}
COPY ./templates/ ${INVENIO_INSTANCE_PATH}/templates/
COPY ./app_data/ ${INVENIO_INSTANCE_PATH}/app_data/
COPY ./translations/ ${INVENIO_INSTANCE_PATH}/translations/
COPY ./ .

# Make sure workspace packages are installed (cds-rdm)
RUN --mount=type=cache,target=/opt/.cache/uv \
    uv sync --frozen --no-dev $BUILD_EXTRAS

# We're caching on a mount, so for any commands that run after this we
# don't want to use the cache (for image filesystem permission reasons)
ENV UV_NO_CACHE=1

# CI=true in `invenio webpack install` makes pnpm apply --frozen-lockfile (pynpm doesn't
# pass it) and skip the interactive prompt that would otherwise abort the build under
# no-TTY.
RUN --mount=type=cache,target=/opt/.cache/pnpm-store \
    invenio collect --verbose && \
    invenio webpack create && \
    CI=true invenio webpack install

COPY ./assets/ ${INVENIO_INSTANCE_PATH}/assets/
COPY ./static/ ${INVENIO_INSTANCE_PATH}/static/
RUN cd ${INVENIO_INSTANCE_PATH}/assets && pnpm run build

COPY ./ .

# node_modules and the webpack sources are only needed to build the bundle; the built
# files live in the instance's static folder.
RUN rm -rf ${INVENIO_INSTANCE_PATH}/assets

# --- Application image ---
# Must stay on the same Python and Debian release as the base image above, so that the
# venv and its compiled extensions still match.
FROM --platform=${BUILD_PLATFORM} python:3.14-slim-trixie

# Shared libraries the venv links against: libcairo2 and libmagickwand for cairocffi and
# wand (loaded through ctypes), the Kerberos ones for python-gssapi and
# requests-kerberos, libpcre2/libxml2/libuuid1 for uwsgi and lxml. procps provides
# ps/top/pkill for interactive shells in a running container.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        ca-certificates \
        krb5-user \
        libcairo2 \
        libgssapi-krb5-2 \
        libmagickwand-7.q16-10 \
        libpcre2-8-0 \
        libuuid1 \
        libxml2 \
        procps

# Kerberos configuration (requests-kerberos / XRootD auth)
COPY ./krb5.conf /etc/krb5.conf

ENV WORKING_DIR=/opt/invenio \
    INVENIO_INSTANCE_PATH=/opt/invenio/var/instance \
    PATH=/opt/invenio/src/.venv/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1

# The venv has no pip, so `uv pip list` is the way to inspect installed dependencies
# from inside a running container.
COPY --from=builder /usr/bin/uv /usr/bin/uvx /usr/local/bin/

COPY --from=builder ${WORKING_DIR} ${WORKING_DIR}

WORKDIR ${WORKING_DIR}/src

# Release reported to Sentry (read automatically by sentry-sdk).
ARG SENTRY_RELEASE
ENV SENTRY_RELEASE=${SENTRY_RELEASE}

EXPOSE 5000
ENTRYPOINT [ "bash", "-c"]
