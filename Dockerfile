# Dockerfile that builds a fully functional image of your app.
#
# This image installs all Python dependencies for your application. It's based
# on Almalinux (https://github.com/inveniosoftware/docker-invenio)
# and includes Pip, Pipenv, Node.js, NPM and some few standard libraries
# Invenio usually needs.
#
# Note: It is important to keep the commands in this file in sync with your
# bootstrap script located in ./scripts/bootstrap.

FROM registry.cern.ch/inveniosoftware/almalinux:1

RUN dnf install -y epel-release
RUN dnf update -y

# XRootD
ARG xrootd_version="5.5.5"
# Repo required to find all the releases of XRootD
RUN dnf config-manager --add-repo https://cern.ch/xrootd/xrootd.repo
RUN if [ ! -z "$xrootd_version" ] ; then XROOTD_V="-$xrootd_version" ; else XROOTD_V="" ; fi && \
    echo "Will install xrootd version: $XROOTD_V (latest if empty)" && \
    dnf install -y xrootd"$XROOTD_V" python3-xrootd"$XROOTD_V"
# /XRootD

# OpenLDAP
RUN dnf install -y openldap-devel

# CRB (Code Ready Builder): equivalent repository to well-known CentOS PowerTools
RUN dnf install -y yum-utils
RUN dnf config-manager --set-enabled crb
# Volume where to mount the keytab as a secrets
# If credentials are passed as username and password with
# KEYTAB_USER and KEYTAB_PWD environment variables, a keytab will be
# generated and stored in KEYTAB_PATH.
RUN dnf install -y krb5-workstation krb5-libs krb5-devel
COPY ./krb5.conf /etc/krb5.conf

# Python and uv configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/opt/.cache/uv \
    UV_COMPILE_BYTECODE=1 \
    UV_FROZEN=1 \
    UV_LINK_MODE=copy \
    UV_NO_MANAGED_PYTHON=1 \
    UV_SYSTEM_PYTHON=1 \
    # Tell uv to use system Python
    UV_PROJECT_ENVIRONMENT=/usr/ \
    UV_PYTHON_DOWNLOADS=never \
    UV_REQUIRE_HASHES=1 \
    UV_VERIFY_HASHES=1

# Get latest version of uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies using uv
ARG BUILD_EXTRAS="--extra sentry --extra xrootd"
RUN --mount=type=cache,target=/opt/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --no-install-workspace --no-editable $BUILD_EXTRAS \
        # (py)xrootd is already installed above using dnf
        --no-install-package=xrootd

COPY site ./site

COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}
COPY ./templates/ ${INVENIO_INSTANCE_PATH}/templates/
COPY ./app_data/ ${INVENIO_INSTANCE_PATH}/app_data/
COPY ./translations/ ${INVENIO_INSTANCE_PATH}/translations/
COPY ./ .

# Make sure workspace packages are installed (cds-rdm)
RUN --mount=type=cache,target=/opt/.cache/uv \
    uv sync --frozen --no-dev $BUILD_EXTRAS \
    # (py)xrootd is already installed above using dnf
    --no-install-package=xrootd

# We're caching on a mount, so for any commands that run after this we
# don't want to use the cache (for image filesystem permission reasons)
ENV UV_NO_CACHE=1

RUN cp -r ./static/. ${INVENIO_INSTANCE_PATH}/static/ && \
    cp -r ./assets/. ${INVENIO_INSTANCE_PATH}/assets/

# Install JS deps from the package-lock file
COPY package-lock.json ${INVENIO_INSTANCE_PATH}/assets/

RUN invenio collect --verbose && \
    invenio webpack buildall

ENTRYPOINT [ "bash", "-c"]
