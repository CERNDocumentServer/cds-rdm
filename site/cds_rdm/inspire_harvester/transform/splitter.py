"""Splits a multi-doc-type INSPIRE record into per-source sub-records."""

from copy import deepcopy

from cds_rdm.inspire_harvester.logger import Logger, hlog
from cds_rdm.inspire_harvester.transform.config import mapper_policy
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.resource_types import (
    INSPIRE_DOCUMENT_TYPE_MAPPING,
)
from cds_rdm.inspire_harvester.utils import assert_unique_ids, deep_merge_all

# Doc types that belong to the arXiv/preprint stream
_PREPRINT_DOC_TYPES = frozenset({"report", "note", "activity report"})
_ARXIV_SOURCES = {"arxiv"}


def _is_arxiv(source: str) -> bool:
    return (source or "").lower() in _ARXIV_SOURCES


class InspireVersionSplitter:
    """Split one INSPIRE record with multiple doc types into two source-filtered sub-records.

    Splitting is triggered when:
    - There are 2+ document_types that map to distinct streams (preprint vs publication)
    - Documents come from at least two source groups (arXiv + non-arXiv)

    The result is always a pair:
        [preprint_sub_record, publication_sub_record]

    Each sub-record has filtered: document_type, dois, titles, abstracts, documents.
    """

    def __init__(self, inspire_record, ctx, cds_id, policy=mapper_policy):
        """Constructor."""
        self.inspire_record = inspire_record
        self.inspire_id = self.inspire_record.get("id")
        self.policy = policy
        self.ctx = ctx
        self.cds_id = cds_id
        self.main_res_type = ctx.resource_type
        self.logger = Logger(inspire_id=self.inspire_id)

    def needs_split(self) -> bool:
        """Determine whether the record needs a split."""
        metadata = self.inspire_record.get("metadata", {})
        doc_types = metadata.get("document_type", [])
        if len(doc_types) <= 1:
            return False

        docs = metadata.get("documents", [])
        dois = metadata.get("dois", [])

        sourced_fields = docs + dois

        has_arxiv = any(_is_arxiv(d.get("source")) for d in sourced_fields)
        has_other = any(not _is_arxiv(d.get("source")) for d in sourced_fields)
        return has_arxiv and has_other

    def split(self):
        """Return [preprint_record, publication_record], or None if split is not applicable."""
        versions = []

        if not self.needs_split():
            return versions

        meta = self.inspire_record["metadata"]
        doc_types = meta.get("document_type", [])

        for doc_type in doc_types:
            self.logger.debug(f"Mapping {doc_type} to version.")
            resource_type = INSPIRE_DOCUMENT_TYPE_MAPPING[doc_type]
            self.logger.info(f"Mapped {doc_type} to {resource_type}.")
            if resource_type is not self.main_res_type:
                version_ctx = MetadataSerializationContext(
                    resource_type=resource_type,
                    inspire_id=self.inspire_id,
                    cds_rdm_id=self.cds_id,
                )
                mappers = self.policy.build_for(resource_type)
                assert_unique_ids(mappers)
                patches = [
                    m.apply(self.inspire_record, version_ctx, self.logger)
                    for m in mappers
                ]

                out_record = deep_merge_all(patches)
                versions.append(out_record)
        self.logger.info(
            f"Mapped {len(versions)} with "
            f"resource types {[v['metadata']['resource_type']['id'] for v in versions]}"
        )
        return versions
