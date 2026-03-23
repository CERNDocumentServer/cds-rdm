# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester context module."""

from dataclasses import dataclass, field
from typing import List, Optional

from cds_rdm.inspire_harvester.transform.resource_types import ResourceType


@dataclass(frozen=True)
class MetadataSerializationContext:
    """Metadata serializing context."""

    resource_type: ResourceType
    inspire_id: str
    cds_rdm_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
