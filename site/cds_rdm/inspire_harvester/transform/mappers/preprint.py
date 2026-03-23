# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from cds_rdm.inspire_harvester.transform.mappers.files import FilesMapper
from cds_rdm.inspire_harvester.transform.mappers.identifiers import DOIMapper
from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


@dataclass(frozen=True)
class PreprintFilesMapper(FilesMapper):
    """Mapper for files."""

    id = "files"

    def filter(self, file):
        """Filters files based on given criteria."""
        material = file.get("material")
        source = file.get("source")
        if not (source or material):
            return False
        if (not material or material == "preprint") and source == "arxiv":
            return True
        if source == "CDS":
            # include it to check the file
            return True
        return False


@dataclass(frozen=True)
class PreprintDOIMapper(DOIMapper):
    """Mapper for DOI identifiers."""

    def filter(self, doi):
        """Filter out DOI based on given criteria."""
        material = doi.get("material")
        if material == "preprint" or not material:
            return True
        return False


@dataclass(frozen=True)
class PreprintTitleMapper(MapperBase):
    """Title mapper."""

    id = "metadata.title"

    def map_value(self, src_record, ctx, logger):
        """Map title value."""
        src_metadata = src_record.get("metadata", {})
        inspire_titles = src_metadata.get("titles", [])
        for title in inspire_titles:
            source = title.get("source", "").lower()
            if source and source == "arxiv":
                return title["title"]
        return inspire_titles[0].get("title")



@dataclass(frozen=True)
class PreprintDescriptionMapper(MapperBase):
    """Description mapper."""

    id = "metadata.description"

    def map_value(self, src_record, ctx, logger):
        """Mapping of abstracts."""
        src_metadata = src_record.get("metadata", {})
        abstracts = src_metadata.get("abstracts", [])
        for abstract in abstracts:
            source = abstract.get("source", "").lower()
            if source and source in ["arxiv", "cds"]:
                return abstract["value"]
            return abstracts[0]["value"]