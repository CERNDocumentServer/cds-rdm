# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""glTF previewer."""

from flask import render_template
from invenio_previewer.proxies import current_previewer
from invenio_previewer.utils import dotted_exts

previewable_extensions = ["gltf"]


def can_preview(file):
    """Check if file can be previewed."""
    return file.is_local() and file.has_extensions(*dotted_exts(previewable_extensions))


def preview(file):
    """Render the glTF previewer."""
    return render_template(
        "cds_rdm/previewer/gltf_previewer.html",
        file=file,
        js_bundles=current_previewer.js_bundles + ["gltf_previewer_js.js"],
        css_bundles=current_previewer.css_bundles + ["gltf_previewer_css.css"],
    )
