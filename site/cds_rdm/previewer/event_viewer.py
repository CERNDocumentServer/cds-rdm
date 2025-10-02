# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL License; see LICENSE file for more details.

"""3D Event viewer."""

from flask import render_template
from invenio_previewer.proxies import current_previewer

# TODO-EV
previewable_extensions = [".aaa"]#["<TODO-extensions>"]


def can_preview(file):
    """Check if file can be previewed."""
    return file.is_local() and file.has_extensions(previewable_extensions)


def preview(file):
    """Render the event viewer."""
    return render_template(
        "cds_rdm/previewer/event_viewer.html",
        file=file,
        js_bundles=current_previewer.js_bundles + ["event_viewer_js.js"],
        css_bundles=current_previewer.css_bundles + ["event_viewer_css.css"],
    )
