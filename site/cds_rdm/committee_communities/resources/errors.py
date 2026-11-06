# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities resource errors."""

import marshmallow as ma
from flask_resources import HTTPJSONException, create_error_handler
from invenio_records_resources.errors import validation_error_to_list_errors
from invenio_records_resources.resources.errors import (
    ErrorHandlersMixin as BaseErrorHandlersMixin,
)

from ..services.errors import (
    CommitteeCommunityAlreadyExistsError,
    CommitteeCommunityNotFoundError,
)


class ErrorHandlersMixin:
    """Mixin to define error handlers."""

    error_handlers = {
        **BaseErrorHandlersMixin.error_handlers,
        CommitteeCommunityNotFoundError: create_error_handler(
            lambda e: HTTPJSONException(code=404, description=str(e.description))
        ),
        CommitteeCommunityAlreadyExistsError: create_error_handler(
            lambda e: HTTPJSONException(code=409, description=str(e.description))
        ),
        ma.ValidationError: create_error_handler(
            lambda e: HTTPJSONException(
                code=400,
                description="A validation error occurred.",
                errors=validation_error_to_list_errors(e),
            )
        ),
    }
