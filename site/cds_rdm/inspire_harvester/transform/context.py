from dataclasses import dataclass, field

from typing import List

from cds_rdm.inspire_harvester.transform.resource_types import ResourceType


@dataclass(frozen=True)
class MetadataSerializationContext:
    resource_type: ResourceType
    inspire_id: str
    errors: List[str] = field(default_factory=list)

    # def __init__(self, resource_type, inspire_id):
    #     self.resource_type = resource_type
    #     self.inspire_id = inspire_id
    #     self.logger = Logger(inspire_id=self.inspire_id)

