# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration data cleaning module."""

from cds_rdm.migration.transform.xml_processing.errors import UnexpectedValue


def clean_str(to_clean):
    """Cleans string values."""
    try:
        return to_clean.strip()
    except AttributeError:
        raise UnexpectedValue
