"""JS/CSS Webpack bundles for My Site."""

from invenio_assets.webpack import WebpackThemeBundle

theme = WebpackThemeBundle(
    __name__,
    "assets",
    default="semantic-ui",
    themes={
        "semantic-ui": dict(
            entry={
                "cds-rdm-detail": "./js/cds_rdm/src/records/detail.js"
            },
        ),
    },
)
