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
