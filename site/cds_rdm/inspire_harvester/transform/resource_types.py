# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from enum import Enum


class ResourceType(str, Enum):
    """Enumeration of resource types for CDS-RDM."""

    ARTICLE = "publication-article"
    BOOK = "publication-book"
    BOOK_CHAPTER = "publication-section"
    CONFERENCE_PAPER = "publication-conferencepaper"
    NOTE = "publication-technicalnote"
    OTHER = "other"
    PREPRINT = "publication-preprint"
    PROCEEDINGS = "publication-conferenceproceedings"
    REPORT = "publication-report"
    THESIS = "publication-dissertation"


# Mapping from INSPIRE document types to CDS-RDM resource types
INSPIRE_DOCUMENT_TYPE_MAPPING = {
    "article": ResourceType.ARTICLE,
    "book": ResourceType.BOOK,
    "report": ResourceType.REPORT,
    "proceedings": ResourceType.PROCEEDINGS,
    "book chapter": ResourceType.BOOK_CHAPTER,
    "thesis": ResourceType.THESIS,
    "note": ResourceType.NOTE,
    "conference paper": ResourceType.CONFERENCE_PAPER,
    "activity report": ResourceType.REPORT,
}


class ResourceTypeDetector:
    """Resource type detector."""

    def __init__(self, inspire_id, logger):
        """Constructor."""
        self.logger = logger
        self.inspire_id = inspire_id
        super().__init__()

    def _select_document_type(self, doc_types):
        """Select document types."""
        priority = {
            v: i
            for i, v in enumerate(
                [
                    "thesis",
                    "conference paper",
                    "article",
                    "book chapter",
                    "book",
                    "proceedings",
                    "report",
                    "activity report",
                    "note",
                ]
            )
        }
        # Select the candidate with the highest priority (lowest rank)
        best_value = min(doc_types, key=lambda v: priority.get(v, float("inf")))
        return best_value

    def _check_if_published_art(self, src_metadata):
        """Check if record is published article.

        follows https://github.com/inspirehep/inspire-schemas/blob/369a2f78189d9711cda8ac83e4e7d9344cc888da/inspire_schemas/readers/literature.py#L338
        """

        def is_citeable(publication_info):
            """Check fields to define if the article is citeable."""

            def _item_has_pub_info(item):
                return all(key in item for key in ("journal_title", "journal_volume"))

            def _item_has_page_or_artid(item):
                return any(key in item for key in ("page_start", "artid"))

            has_pub_info = any(_item_has_pub_info(item) for item in publication_info)
            has_page_or_artid = any(
                _item_has_page_or_artid(item) for item in publication_info
            )

            return has_pub_info and has_page_or_artid

        pub_info = src_metadata.get("publication_info", [])

        citeable = pub_info and is_citeable(pub_info)

        submitted = "dois" in src_metadata and any(
            "journal_title" in el for el in pub_info
        )

        return citeable or submitted

    def detect(self, src_metadata):
        """Mapping of INSPIRE document type to resource type."""
        rt = None
        errors = []
        document_types = src_metadata.get("document_type", [])

        self.logger.debug(f"Processing document types: {document_types}")

        if not document_types:
            errors.append(f"No document_type found in INSPIRE#{self.inspire_id}.")
            return None, errors

        # Check for multiple document types - fail for now
        if len(document_types) > 1:
            document_type = self._select_document_type(document_types)
            self.logger.info(
                f"Multiple document types found: {document_types}, mapped to {document_type}"
            )
        else:
            # Get the single document type
            document_type = document_types[0]

        self.logger.debug(f"Document type found: {document_type}")

        # Use the reusable mapping
        try:
            rt = INSPIRE_DOCUMENT_TYPE_MAPPING[document_type]
        except KeyError:
            errors.append(
                f"Error: Couldn't find resource type mapping rule for "
                f"document_type '{document_type}'. INSPIRE#{self.inspire_id}. "
                f"Available mappings: {list(INSPIRE_DOCUMENT_TYPE_MAPPING.keys())}"
            )
            self.logger.error(f"Unmapped document type: {document_type}")

        if document_type == "article" and not self._check_if_published_art(
            src_metadata
        ):
            # preprint type does not exist in inspire, it is computed
            rt = ResourceType.PREPRINT

        return rt, errors


# inspire enums https://github.com/inspirehep/inspire-schemas/blob/369a2f78189d9711cda8ac83e4e7d9344cc888da/inspire_schemas/records/elements

# materials
# - addendum
# - additional material
# - data
# - editorial note
# - erratum
# - part
# - preprint
# - publication
# - reprint
# - software
# - translation
# - version

# document types
# - activity report
# - article
# - book
# - book chapter
# - conference paper
# - note
# - proceedings
# - report
# - thesis
