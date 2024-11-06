import re

# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities module."""


def is_cds(val):
    """Test if argument is a valid CDS identifier in the form of cds:a:XXXXXXXXXX."""
    pattern = r"^cds:a:.{10}$"
    return bool(re.match(pattern, val))
