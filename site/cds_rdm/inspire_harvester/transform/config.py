from enum import Enum

from cds_rdm.inspire_harvester.transform.mappers.basic_metadata import \
    ResourceTypeMapper, TitleMapper, AdditionalTitlesMapper, PublisherMapper, \
    PublicationDateMapper, CopyrightMapper, DescriptionMapper, \
    AdditionalDescriptionsMapper, SubjectsMapper, LanguagesMapper
from cds_rdm.inspire_harvester.transform.mappers.contributors import AuthorsMapper, \
    ContributorsMapper
from cds_rdm.inspire_harvester.transform.mappers.custom_fields import ImprintMapper, \
    CERNFieldsMapper
from cds_rdm.inspire_harvester.transform.mappers.files import FilesMapper
from cds_rdm.inspire_harvester.transform.mappers.identifiers import DOIMapper, \
    IdentifiersMapper, RelatedIdentifiersMapper
from cds_rdm.inspire_harvester.transform.mappers.thesis import ThesisDefenceDateMapper, \
    ThesisPublicationDateMapper
from cds_rdm.inspire_harvester.transform.policies import MapperPolicy
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType

BASE_MAPPERS = (FilesMapper(),
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
                RelatedIdentifiersMapper()
                )
THESIS_MAPPERS = (ThesisDefenceDateMapper(),)

inspire_mapper_policy = MapperPolicy(base=BASE_MAPPERS)

mapper_policy = MapperPolicy(
    base=BASE_MAPPERS,
    add={
        ResourceType.THESIS: THESIS_MAPPERS,
    },
    replace={
        (ResourceType.THESIS, "metadata.publication_date"):
         ThesisPublicationDateMapper(),
        # (ResourceType.ARTICLE, "metadata.publication_info"): ArticlePublicationInfoMapper(),
        # (ResourceType.CONFERENCE_PAPER, "metadata.publication_info"): ConferencePublicationInfoMapper(),
    },
    # if you had a generic publication_info mapper in base, you'd replace it here
)
