from flask import current_app
from werkzeug.local import LocalProxy

current_authors_service = LocalProxy(
    lambda: current_app.extensions["cds-rdm"].authors_service
)
"""Proxy for the currently instantiated authors service."""
