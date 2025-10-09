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
                "gltf_previewer_js": "./js/cds-rdm-site/previewer/gltf-previewer.js",
                "gltf_previewer_css": "./less/cds-rdm-site/previewer/gltf-previewer.less",
            },
        ),
    },
)
