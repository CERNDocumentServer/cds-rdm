# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

import re
from dataclasses import dataclass

from babel_edtf import parse_edtf
from edtf.parser.grammar import ParseException

from .contributors import ContributorsMapper
from .mapper import MapperBase


@dataclass(frozen=True)
class ThesisPublicationDateMapper(MapperBase):
    """Mapper for thesis publication date."""

    id = "metadata.publication_date"

    def map_value(self, src_record, ctx, logger):
        """Mapping of INSPIRE thesis_info.date to metadata.publication_date."""
        src_metadata = src_record.get("metadata", {})
        imprints = src_metadata.get("imprints", [])
        imprint_date = imprints[0].get("date") if imprints else None
        thesis_info = src_metadata.get("thesis_info", {})
        thesis_date = thesis_info.get("date") or (
            imprint_date if imprint_date else None
        )

        if thesis_date is None:
            ctx.errors.append(
                f"Thesis publication date missing (thesis_info and imprint)."
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

    def map_value(self, src_record, ctx, logger):
        """Apply thesis field mapping."""
        src_metadata = src_record.get("metadata", {})
        thesis_info = src_metadata.get("thesis_info", {})
        defense_date = thesis_info.get("defense_date")
        return defense_date


@dataclass(frozen=True)
class ThesisUniversityMappers(MapperBase):
    """Mapper for thesis university."""

    id = "custom_fields.thesis:thesis.university"

    def map_value(self, src_record, ctx, logger):
        """Apply thesis field mapping."""
        src_metadata = src_record.get("metadata", {})
        thesis_info = src_metadata.get("thesis_info", {})
        institutions = thesis_info.get("institutions")
        if institutions:
            university = institutions[0].get("name")
            if university:
                university = re.sub(r'\bU\.(?=\s|$)', 'University', university)
                return university



@dataclass(frozen=True)
class ThesisTypeMappers(MapperBase):
    """Mapper for thesis type."""

    id = "custom_fields.thesis:thesis.type"

    def map_value(self, src_record, ctx, logger):
        """Apply thesis field mapping."""
        src_metadata = src_record.get("metadata", {})
        thesis_info = src_metadata.get("thesis_info", {})
        type = thesis_info.get("degree_type")
        return type



@dataclass(frozen=True)
class ThesisContributorsMapper(ContributorsMapper):
    """Mapper for thesis contributors including supervisors."""

    id = "metadata.contributors"

    def map_value(self, src_record, ctx, logger):
        """Map thesis contributors and supervisors."""
        src_metadata = src_record.get("metadata", {})
        contributors = super().map_value(src_record, ctx, logger)

        _supervisors = src_metadata.get("supervisors")
        supervisors = self._transform_creatibutors(_supervisors, ctx)
        if not contributors:
            contributors = []
        if not supervisors:
            supervisors = []

        return contributors + supervisors


@dataclass(frozen=True)
class ThesisProgrammesMapper(MapperBase):
    """Mapper for thesis programmes with default value.

    Sets the default "No program participation" value for harvested thesis records.
    The writer conditionally applies this on create vs update.
    """

    id = "custom_fields.cern:programmes"

    def map_value(self, src_metadata, ctx, logger):
        """Set default programme value.

        Returns the "None" vocabulary reference (No program participation).
        INSPIRE doesn't provide programme data, so we always return the default.
        """
        logger.debug("Setting default programme 'None' for thesis record")
        return {"id": "None"}


