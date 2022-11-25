# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM base migration model."""

from .overdo import CdsOverdo


class CDSBase(CdsOverdo):
    """Translation Index for CDS Books."""


model = CDSBase(bases=(), entry_point_group=None)
