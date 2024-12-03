# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2023-2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM."""

from .ext import CDS_RDM_REST, CDS_RDM_UI

__version__ = "1.0.22"

__all__ = (
    "__version__",
    "CDS_RDM_UI",
    "CDS_RDM_REST",
)
