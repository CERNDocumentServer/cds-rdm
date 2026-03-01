# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Harvester download resources."""

from .config import HarvesterDownloadResourceConfig
from .resource import HarvesterDownloadResource

__all__ = ("HarvesterDownloadResource", "HarvesterDownloadResourceConfig")
