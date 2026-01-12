# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE to CDS policies module."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase as Mapper
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType


@dataclass(frozen=True)
class MapperPolicy:
    """Mapper policy class."""

    base: Tuple[Mapper, ...]
    # per type:
    add: Dict[ResourceType, Tuple[Mapper, ...]] = field(default_factory=dict)
    replace: Dict[Tuple[ResourceType, str], Mapper] = field(default_factory=dict)
    remove: Dict[ResourceType, Tuple[str, ...]] = field(default_factory=dict)

    def build_for(self, rt: ResourceType) -> List[Mapper]:
        """Build mapper for specified resource type."""
        # start with base
        mappers: List[Mapper] = list(self.base)

        # remove by id
        remove_ids = set(self.remove.get(rt, ()))
        mappers = [m for m in mappers if m.id not in remove_ids]

        # replace by (rt, mapper_id)
        # replacement is done by id match
        replacements = {
            mid: mapper for (rtype, mid), mapper in self.replace.items() if rtype == rt
        }
        if replacements:
            new_list = []
            for m in mappers:
                new_list.append(replacements.get(m.id, m))
            mappers = new_list

        # add extra mappers for this type
        mappers.extend(self.add.get(rt, ()))

        # optional: enforce stable ordering if needed
        return mappers
