# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException

from .contributors import ContributorsMapper
from .mapper import MapperBase


@dataclass(frozen=True)
class ThesisPublicationDateMapper(MapperBase):
    """Mapper for thesis publication date."""

    id = "metadata.publication_date"

    def map_value(self, src_metadata, ctx, logger):
        """Mapping of INSPIRE thesis_info.date to metadata.publication_date."""
        imprints = src_metadata.get("imprints", [])
        imprint_date = imprints[0].get("date") if imprints else None
        thesis_info = src_metadata.get("thesis_info", {})
        thesis_date = thesis_info.get("date") or (
            imprint_date if imprint_date else None
        )

        if thesis_date is None:
            ctx.errors.append(
                f"Thesis publication date transform failed. INSPIRE#{ctx.inspire_id}."
            )
            return None
        try:
            parsed_date = str(parse_edtf(thesis_date))
            return parsed_date
        except ParseException as e:
            ctx.errors.append(
                f"Publication date transformation failed."
                f"INSPIRE#{ctx.inspire_id}. Date: {thesis_date}. "
                f"Error: {e}."
            )
            return None


@dataclass(frozen=True)
class ThesisDefenceDateMapper(MapperBase):
    """Mapper for thesis defence date."""

    id = "custom_fields.thesis:thesis.defense_date"

    def map_value(self, src_metadata, ctx, logger):
        """Apply thesis field mapping."""
        thesis_info = src_metadata.get("thesis_info", {})
        defense_date = thesis_info.get("defense_date")
        return defense_date


@dataclass(frozen=True)
class ThesisUniversityMappers(MapperBase):
    """Mapper for thesis university."""

    id = "custom_fields.thesis:thesis.university"

    def map_value(self, src_metadata, ctx, logger):
        """Apply thesis field mapping."""
        thesis_info = src_metadata.get("thesis_info", {})
        institutions = thesis_info.get("institutions")
        if institutions:
            university = institutions[0].get("name")
            return university



@dataclass(frozen=True)
class ThesisTypeMappers(MapperBase):
    """Mapper for thesis type."""

    id = "custom_fields.thesis:thesis.type"

    def map_value(self, src_metadata, ctx, logger):
        """Apply thesis field mapping."""
        thesis_info = src_metadata.get("thesis_info", {})
        type = thesis_info.get("degree_type")
        return type



@dataclass(frozen=True)
class ThesisContributorsMapper(ContributorsMapper):
    """Mapper for thesis contributors including supervisors."""

    id = "metadata.contributors"

    def map_value(self, src_metadata, ctx, logger):
        """Map thesis contributors and supervisors."""
        contributors = super().map_value(src_metadata, ctx, logger)

        _supervisors = src_metadata.get("supervisors")
        supervisors = self._transform_creatibutors(_supervisors, ctx)
        return contributors + supervisors


