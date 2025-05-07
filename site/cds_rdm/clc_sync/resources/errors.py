# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Errors."""

import marshmallow as ma
from flask_resources import HTTPJSONException, create_error_handler
from invenio_records_resources.errors import validation_error_to_list_errors

from ..services.errors import CLCSyncAlreadyExistsError, CLCSyncNotExistsError


class HTTPJSONValidationException(HTTPJSONException):
    """HTTP exception serializing to JSON and reflecting Marshmallow errors."""

    description = "A validation error occurred."

    def __init__(self, exception):
        """Constructor."""
        super().__init__(code=400, errors=validation_error_to_list_errors(exception))


class ErrorHandlersMixin:
    """Mixin to define error handlers."""

    error_handlers = {
        CLCSyncNotExistsError: create_error_handler(
            lambda e: HTTPJSONException(
                code=404,
                description=e.description,
            )
        ),
        CLCSyncAlreadyExistsError: create_error_handler(
            lambda e: HTTPJSONException(
                code=409,
                description=e.description,
            )
        ),
        ma.ValidationError: create_error_handler(
            lambda e: HTTPJSONValidationException(e)
        ),
    }
