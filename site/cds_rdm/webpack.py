# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL License; see LICENSE file for more details.

"""JS/CSS Webpack bundles."""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    "assets",
    default="semantic-ui",
    themes={
        "semantic-ui": dict(
            entry={
                "event_viewer_js": "./js/previewer/event-viewer.js",
                "event_viewer_css": "./less/cds-rdm/previewer/event-viewer.less",
            },
        ),
    },
)
