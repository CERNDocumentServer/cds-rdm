# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS files utilities."""

import mimetypes
import os
import unicodedata
from urllib.parse import quote, urlsplit, urlunsplit

import requests
from flask import current_app, make_response, request
from invenio_files_rest.helpers import sanitize_mimetype
from invenio_files_rest.storage.pyfs import pyfs_storage_factory

try:
    from invenio_xrootd.storage import EOSFileStorage as BaseFileStorage
    from requests_kerberos import DISABLED, HTTPKerberosAuth
except ImportError:
    # fake requests_kerberos
    HTTPKerberosAuth = type("obj", (object,), {})
    DISABLED = 3
    # use base PyFSFileStorage instead
    from invenio_files_rest.storage.pyfs import \
        PyFSFileStorage as BaseFileStorage


class OffloadFileStorage(BaseFileStorage):
    """Offload file downloads to another server."""

    def _get_auth_session(self):
        """Get a requests session with authentication configured.

        If X.509 is enabled, it will be used, otherwise kerberos will be used.
        """
        s = requests.Session()
        x509_enabled = current_app.config.get("CDS_EOS_OFFLOAD_AUTH_X509", False)
        cert = current_app.config.get("CDS_EOS_OFFLOAD_X509_CERT_PATH")
        key = current_app.config.get("CDS_EOS_OFFLOAD_X509_KEY_PATH")
        if x509_enabled and cert and key:
            s.cert = (cert, key)
            s.verify = False
        else:
            # Default to kerberos
            s.auth = HTTPKerberosAuth(DISABLED)
            s.verify = False
        return s

    def _get_eos_redirect_path(self):
        """Get the real path of the file streamed from another server."""
        host = current_app.config["CDS_EOS_OFFLOAD_HTTPHOST"]
        redirect_base_path = current_app.config["CDS_EOS_OFFLOAD_REDIRECT_BASE_PATH"]
        base_path = urlsplit(self.fileurl).path
        session = self._get_auth_session()
        eos_resp = session.get(
            f"{host}/{base_path}",
            allow_redirects=False,
            timeout=5,
        )
        if eos_resp.status_code != 307:
            raise Exception(
                f"EOS redirect failed "
                f"with response code:{eos_resp.status_code} "
                f" and error: {eos_resp.text}"
            )

        eos_url = eos_resp.next.url
        eos_url_parts = urlsplit(eos_url)
        redirect_path = f"{redirect_base_path}/{eos_url_parts.scheme}/{eos_url_parts.hostname}/{eos_url_parts.port}/{eos_url_parts.path}"
        return urlunsplit(("", "", redirect_path, eos_url_parts.query, ""))

    def send_file(
        self,
        filename,
        mimetype=None,
        restricted=True,
        checksum=None,
        trusted=False,
        chunk_size=None,
        as_attachment=False,
        **kwargs,
    ):
        """Send file."""
        offload_enabled = current_app.config["FILES_REST_XSENDFILE_ENABLED"]

        # No need to proxy HEAD requests
        should_offload = request.method != "HEAD" and offload_enabled

        if not should_offload:
            # don't offload if not enabled
            return super().send_file(
                filename,
                mimetype=mimetype,
                restricted=restricted,
                checksum=checksum,
                trusted=trusted,
                chunk_size=chunk_size,
                as_attachment=as_attachment,
            )

        should_offload_to_eos = current_app.config["CDS_EOS_OFFLOAD_ENABLED"]

        should_offload_locally = (
            current_app.config["CDS_LOCAL_OFFLOAD_ENABLED"]
            and filename in current_app.config["CDS_LOCAL_OFFLOAD_FILES"]
        )

        if should_offload_locally:
            response = make_response()

            try:
                path = os.path.join(
                    current_app.config["CDS_LOCAL_OFFLOAD_STORAGE"], filename
                )
                response.headers["X-Accel-Redirect"] = path
            except Exception as ex:
                current_app.logger.exception(ex)
                # continue to try eos offload

        if should_offload_to_eos:
            response = make_response()

            try:
                response.headers["X-Accel-Redirect"] = self._get_eos_redirect_path()
            except Exception as ex:
                current_app.logger.exception(ex)
                # fallback to download via app
                return super().send_file(
                    filename,
                    mimetype=mimetype,
                    restricted=restricted,
                    checksum=checksum,
                    trusted=trusted,
                    chunk_size=chunk_size,
                    as_attachment=as_attachment,
                )
        response.headers["X-Accel-Buffering"] = "yes"
        response.headers["X-Accel-Limit-Rate"] = "off"

        mimetype = mimetypes.guess_type(filename)[0]
        if mimetype is not None:
            mimetype = sanitize_mimetype(mimetype, filename=filename)

        if mimetype is None:
            mimetype = "application/octet-stream"

        response.mimetype = mimetype

        # Force Content-Disposition for application/octet-stream to prevent
        # Content-Type sniffing.
        # (from invenio-files-rest)
        if as_attachment or mimetype == "application/octet-stream":
            # See https://github.com/pallets/flask/commit/0049922f2e690a6d
            try:
                filenames = {"filename": filename.encode("latin-1")}
            except UnicodeEncodeError:
                # safe = RFC 5987 attr-char
                quoted = quote(filename, safe="!#$&+-.^_`|~")

                filenames = {"filename*": "UTF-8''%s" % quoted}
                encoded_filename = unicodedata.normalize("NFKD", filename).encode(
                    "latin-1", "ignore"
                )
                if encoded_filename:
                    filenames["filename"] = encoded_filename
            response.headers.set("Content-Disposition", "attachment", **filenames)
        else:
            response.headers.set("Content-Disposition", "inline")

        # Security-related headers for the download (from invenio-files-rest)
        response.headers["Content-Security-Policy"] = "default-src 'none';"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["X-Frame-Options"] = "deny"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # add offload header
        response.headers["Invenio-Offload"] = "true"
        return response


def storage_factory(**kwargs):
    """Create custom storage factory to enable file offloading."""
    return pyfs_storage_factory(filestorage_class=OffloadFileStorage, **kwargs)
