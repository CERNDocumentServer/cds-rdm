"""Splits a multi-doc-type INSPIRE record into per-source sub-records."""
from cds_rdm.inspire_harvester.logger import Logger, hlog
from cds_rdm.inspire_harvester.transform.config import mapper_policy
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.resource_types import \
    INSPIRE_DOCUMENT_TYPE_MAPPING
from cds_rdm.inspire_harvester.utils import assert_unique_ids, deep_merge_all
from copy import deepcopy

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
        self.inspire_record = inspire_record
        self.inspire_id = self.inspire_record.get("id")
        self.policy = policy
        self.ctx = ctx
        self.cds_id = cds_id
        self.main_res_type = ctx.resource_type.value
        self.logger = Logger(inspire_id=self.inspire_id)

    def needs_split(self) -> bool:
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
        if not self.needs_split():
            return None

        meta = self.inspire_record["metadata"]
        doc_types = meta.get("document_type", [])
        versions = []

        for doc_type in doc_types:
            self.logger.debug(f"Mapping {doc_type} to version.")
            resource_type = INSPIRE_DOCUMENT_TYPE_MAPPING[doc_type].value
            self.logger.info(f"Mapped {doc_type} to {resource_type}.")
            if resource_type is not self.main_res_type:
                version_ctx = MetadataSerializationContext(
                    resource_type=resource_type,
                    inspire_id=self.inspire_id,
                    cds_rdm_id=self.cds_id
                )
                mappers = self.policy.build_for(resource_type)
                assert_unique_ids(mappers)
                patches = [m.apply(self.inspire_record, version_ctx, self.logger) for m in
                           mappers]

                out_record = deep_merge_all(patches)
                versions.append(out_record)
        self.logger.info(
            f"Mapped {len(versions)} with "
            f"resource types {[v['metadata']['resource_type']['id'] for v in versions]}")
        return versions

        preprint_types = [dt for dt in doc_types if dt in _PREPRINT_DOC_TYPES]
        pub_types = [dt for dt in doc_types if dt not in _PREPRINT_DOC_TYPES]

        if not preprint_types or not pub_types:
            return None  # can't partition cleanly, fall back to single-version logic

        preprint = deepcopy(self.inspire_record)
        publication = deepcopy(self.inspire_record)

        # document_type
        preprint["metadata"]["document_type"] = preprint_types
        publication["metadata"]["document_type"] = pub_types

        # documents — split by source
        docs = meta.get("documents", [])
        preprint["metadata"]["documents"] = [d for d in docs if
                                             _is_arxiv(d.get("source"))]
        publication["metadata"]["documents"] = [d for d in docs if
                                                not _is_arxiv(d.get("source"))]

        # dois — split by material
        # preprint:    material=preprint  (includes the CDS DOI sourced from arXiv)
        # publication: material=publication AND non-arXiv source
        #              (deduplication of same-value entries happens in DOIMapper)
        dois = meta.get("dois", [])
        preprint["metadata"]["dois"] = [
            d for d in dois if d.get("material") == "preprint"
        ]
        publication["metadata"]["dois"] = [
            d for d in dois
            if d.get("material") == "publication" and not _is_arxiv(d.get("source"))
        ]

        # titles — split by source
        titles = meta.get("titles", [])
        preprint["metadata"]["titles"] = [t for t in titles if
                                          _is_arxiv(t.get("source"))]
        publication["metadata"]["titles"] = [t for t in titles if
                                             not _is_arxiv(t.get("source"))]

        # abstracts — split by source
        abstracts = meta.get("abstracts", [])
        preprint["metadata"]["abstracts"] = [a for a in abstracts if
                                             _is_arxiv(a.get("source"))]
        publication["metadata"]["abstracts"] = [a for a in abstracts if
                                                not _is_arxiv(a.get("source"))]

        return [preprint, publication]
