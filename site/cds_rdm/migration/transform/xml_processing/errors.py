# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration errors module."""

from dojson.errors import DoJSONException


class LossyConversion(DoJSONException):
    """Data lost during migration."""

    def __init__(self, missing=None, *args, **kwargs):
        """Exception custom initialisation."""
        self.missing = missing
        self.message = "Lossy conversion: {0}".format(self.missing or "")
        super().__init__(*args)


class CDSMigrationException(DoJSONException):
    """CDSDoJSONException class."""

    message = None

    def __init__(self, message=None, field=None, subfield=None, *args, **kwargs):
        """Constructor."""
        self.subfield = subfield
        self.field = field

        self.message = f"{self.message}: {field}{subfield} ({message}"

        super(CDSMigrationException, self).__init__(*args)


class RecordModelMissing(CDSMigrationException):
    """Missing record model exception."""

    message = "[Record did not match any available model]"


class UnexpectedValue(CDSMigrationException):
    """The corresponding value is unexpected."""

    message = "[UNEXPECTED INPUT VALUE]"


class MissingRequiredField(CDSMigrationException):
    """The corresponding value is required."""

    message = "[MISSING REQUIRED FIELD]"
