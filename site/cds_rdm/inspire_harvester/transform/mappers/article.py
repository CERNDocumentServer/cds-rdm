# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from flask import current_app

from cds_rdm.inspire_harvester.transform.mappers.basic_metadata import TitleMapper
from cds_rdm.inspire_harvester.transform.mappers.files import FilesMapper
from cds_rdm.inspire_harvester.transform.mappers.identifiers import DOIMapper
from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


@dataclass(frozen=True)
class ArticleFilesMapper(FilesMapper):
    """Mapper for files."""

    def filter(self, file):
        """Filters files based on given criteria."""
        material = file.get("material")
        source = file.get("source")
        if not (source or material):
            return False
        if (not material or material == "publication") and source != "arxiv":
            return True


@dataclass(frozen=True)
class ArticleDOIMapper(DOIMapper):
    """Mapper for DOI identifiers."""

    def filter(self, doi):
        """Filter out DOI based on given criteria."""
        material = doi.get("material")
        value = doi.get("value")
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        if material == "publication":
            return True

        if not value.startswith(DATACITE_PREFIX):
            return True
        return False


@dataclass(frozen=True)
class ArticleTitleMapper(MapperBase):
    """Title mapper."""

    id = "metadata.title"

    def map_value(self, src_record, ctx, logger):
        """Map title value."""
        src_metadata = src_record.get("metadata", {})
        inspire_titles = src_metadata.get("titles", [])
        for title in inspire_titles:
            source = title.get("source", "").lower()
            if source and source not in ["arxiv", "cds"]:
                return title["title"]
        return inspire_titles[0].get("title")


@dataclass(frozen=True)
class ArticleDescriptionMapper(MapperBase):
    """Description mapper."""

    id = "metadata.description"

    def map_value(self, src_record, ctx, logger):
        """Mapping of abstracts."""
        src_metadata = src_record.get("metadata", {})
        abstracts = src_metadata.get("abstracts", [])
        for abstract in abstracts:
            source = abstract.get("source", "").lower()
            if source and source not in ["arxiv", "cds"]:
                return abstract["value"]
            return abstracts[0]["value"]