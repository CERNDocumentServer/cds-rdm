# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE to CDS harvester context module."""

from dataclasses import dataclass, field
from typing import List

from cds_rdm.inspire_harvester.transform.resource_types import ResourceType


@dataclass(frozen=True)
class MetadataSerializationContext:
    resource_type: ResourceType
    inspire_id: str
    errors: List[str] = field(default_factory=list)
