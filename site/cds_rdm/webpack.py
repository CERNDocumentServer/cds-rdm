# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""JS/CSS Webpack bundles."""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    "assets",
    default="semantic-ui",
    themes={
        "semantic-ui": dict(
            entry={
                "gltf_previewer_js": "./js/cds_rdm/previewers/gltf-previewer.js",
                "gltf_previewer_css": "./less/cds_rdm/previewers/gltf-previewer.less",
            },
            dependencies={
                "three": "^0.180.0",
                "three-addons": "^1.2.0",
            },
        ),
    },
)
