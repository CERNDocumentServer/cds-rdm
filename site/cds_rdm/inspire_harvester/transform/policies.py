from dataclasses import dataclass, field

from typing import Dict, Tuple, List

from cds_rdm.inspire_harvester.transform.resource_types import ResourceType
from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase as Mapper

@dataclass(frozen=True)
class MapperPolicy:
    base: Tuple[Mapper, ...]
    # per type:
    add: Dict[ResourceType, Tuple[Mapper, ...]] = field(default_factory=dict)
    replace: Dict[Tuple[ResourceType, str], Mapper] = field(default_factory=dict)
    remove: Dict[ResourceType, Tuple[str, ...]] = field(default_factory=dict)

    def build_for(self, rt: ResourceType) -> List[Mapper]:
        # start with base
        mappers: List[Mapper] = list(self.base)

        # remove by id
        remove_ids = set(self.remove.get(rt, ()))
        mappers = [m for m in mappers if m.id not in remove_ids]

        # replace by (rt, mapper_id)
        # replacement is done by id match
        replacements = {
            mid: mapper
            for (rtype, mid), mapper in self.replace.items()
            if rtype == rt
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