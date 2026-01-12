# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""INSPIRE to CDS harvester config module."""

from cds_rdm.inspire_harvester.transform.mappers.basic_metadata import (
    AdditionalDescriptionsMapper,
    AdditionalTitlesMapper,
    CopyrightMapper,
    DescriptionMapper,
    LanguagesMapper,
    PublicationDateMapper,
    PublisherMapper,
    ResourceTypeMapper,
    SubjectsMapper,
    TitleMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.contributors import (
    AuthorsMapper,
    ContributorsMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.custom_fields import (
    CERNFieldsMapper,
    ImprintMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.files import FilesMapper
from cds_rdm.inspire_harvester.transform.mappers.identifiers import (
    DOIMapper,
    IdentifiersMapper,
    RelatedIdentifiersMapper,
)
from cds_rdm.inspire_harvester.transform.mappers.thesis import (
    ThesisDefenceDateMapper,
    ThesisPublicationDateMapper,
)
from cds_rdm.inspire_harvester.transform.policies import MapperPolicy
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType

BASE_MAPPERS = (
    FilesMapper(),
    ResourceTypeMapper(),
    DOIMapper(),
    TitleMapper(),
    AdditionalTitlesMapper(),
    AuthorsMapper(),
    ContributorsMapper(),
    PublisherMapper(),
    PublicationDateMapper(),
    CopyrightMapper(),
    DescriptionMapper(),
    AdditionalDescriptionsMapper(),
    SubjectsMapper(),
    LanguagesMapper(),
    ImprintMapper(),
    CERNFieldsMapper(),
    IdentifiersMapper(),
    RelatedIdentifiersMapper(),
)
THESIS_MAPPERS = (ThesisDefenceDateMapper(),)

inspire_mapper_policy = MapperPolicy(base=BASE_MAPPERS)

mapper_policy = MapperPolicy(
    base=BASE_MAPPERS,
    add={
        ResourceType.THESIS: THESIS_MAPPERS,
    },
    # if you had a generic mapper in base, you'd replace it here
    replace={
        (
            ResourceType.THESIS,
            "metadata.publication_date",
        ): ThesisPublicationDateMapper(),
    },

)
