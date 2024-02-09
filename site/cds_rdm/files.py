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
from urllib.parse import quote

from flask import current_app, make_response, request
from invenio_files_rest.helpers import sanitize_mimetype
from invenio_files_rest.storage.pyfs import PyFSFileStorage as BaseFileStorage
from invenio_files_rest.storage.pyfs import pyfs_storage_factory


class OffloadFileStorage(BaseFileStorage):
    """Offload file downloads to another server."""

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
        # No need to proxy HEAD requests
        offload_enabled = (
            request.method != "HEAD"
            and current_app.config["FILES_REST_XSENDFILE_ENABLED"]
        )

        should_offload_locally = (
            current_app.config["CDS_LOCAL_OFFLOAD_ENABLED"]
            and filename in current_app.config["CDS_LOCAL_OFFLOAD_FILES"]
        )

        if offload_enabled and should_offload_locally:
            response = make_response()

            try:
                path = os.path.join(
                    current_app.config["CDS_LOCAL_OFFLOAD_STORAGE"], filename
                )
                response.headers["X-Accel-Redirect"] = path
            except Exception as ex:
                current_app.logger.exception(ex)
                # fallback to normal file download
                return super().send_file(filename, **kwargs)

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
            return response
        else:
            return super().send_file(filename, **kwargs)


def storage_factory(**kwargs):
    """Create custom storage factory to enable file offloading."""
    return pyfs_storage_factory(filestorage_class=OffloadFileStorage, **kwargs)
