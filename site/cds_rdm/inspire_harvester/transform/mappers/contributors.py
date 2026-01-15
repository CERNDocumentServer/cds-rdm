# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


class CreatibutorsMapper(MapperBase):
    """Base class for mapping creatibutors (creators and contributors)."""

    def _transform_author_identifiers(self, author):
        """Transform ids of authors. Keeping only ORCID and CDS."""
        author_ids = author.get("ids", [])
        processed_identifiers = []

        schemes_map = {
            "INSPIRE ID": "inspire_author",
            "ORCID": "orcid",
        }

        for author_id in author_ids:
            author_scheme = author_id.get("schema")
            if author_scheme in schemes_map.keys():
                processed_identifiers.append(
                    {
                        "identifier": author_id.get("value"),
                        "scheme": schemes_map[author_scheme],
                    }
                )

        return processed_identifiers

    def _transform_author_affiliations(self, author):
        """Transform affiliations."""
        affiliations = author.get("affiliations", [])
        mapped_affiliations = []

        for affiliation in affiliations:
            value = affiliation.get("value")
            if value:
                mapped_affiliations.append({"name": value})

        return mapped_affiliations

    def _transform_creatibutors(self, authors, ctx):
        """Transform creatibutors."""
        creatibutors = []
        try:
            for author in authors:
                first_name = author.get("first_name")
                last_name = author.get("last_name")
                full_name = author.get("full_name")

                rdm_creatibutor = {
                    "person_or_org": {
                        "type": "personal",
                    }
                }

                if first_name:
                    rdm_creatibutor["person_or_org"]["given_name"] = first_name
                if last_name:
                    rdm_creatibutor["person_or_org"]["family_name"] = last_name
                else:
                    last_name, first_name = full_name.split(", ")
                    rdm_creatibutor["person_or_org"]["family_name"] = last_name
                if first_name and last_name:
                    rdm_creatibutor["person_or_org"]["name"] = (
                        last_name + ", " + first_name
                    )

                creator_affiliations = self._transform_author_affiliations(author)
                creator_identifiers = self._transform_author_identifiers(author)
                role = author.get("inspire_roles")

                if creator_affiliations:
                    rdm_creatibutor["affiliations"] = creator_affiliations

                if creator_identifiers:
                    rdm_creatibutor["person_or_org"][
                        "identifiers"
                    ] = creator_identifiers

                if role:
                    rdm_creatibutor["role"] = {"id": role[0]}
                creatibutors.append(rdm_creatibutor)
            return creatibutors
        except Exception as e:
            ctx.errors.append(
                f"Mapping authors  field failed. INSPIRE#{ctx.inspire_id}. Error: {e}."
            )
            return None

    def map_value(self, src, ctx, logger):
        """Map creatibutors value (to be implemented by subclasses)."""
        pass


creators_roles = ["author", "editor"]


@dataclass(frozen=True)
class AuthorsMapper(CreatibutorsMapper):
    """Mapper for authors/creators."""

    id = "metadata.creators"

    def map_value(self, src_metadata, ctx, logger):
        """Map authors to RDM creators."""
        authors = src_metadata.get("authors", [])
        creators = []
        for author in authors:
            inspire_roles = author.get("inspire_roles")
            if not inspire_roles:
                creators.append(author)
            else:
                for role in creators_roles:
                    if role in inspire_roles:
                        creators.append(author)

        corporate_authors = src_metadata.get("corporate_author", [])
        mapped_corporate_authors = []
        for corporate_author in corporate_authors:
            contributor = {
                "person_or_org": {
                    "type": "organizational",
                    "name": corporate_author,
                },
            }
            mapped_corporate_authors.append(contributor)

        return self._transform_creatibutors(creators, ctx) + mapped_corporate_authors


@dataclass(frozen=True)
class ContributorsMapper(CreatibutorsMapper):
    """Mapper for contributors."""

    id = "metadata.contributors"

    def map_value(self, src_metadata, ctx, logger):
        """Map authors to RDM contributors."""
        authors = src_metadata.get("authors", [])
        contributors = []

        for author in authors:
            inspire_roles = author.get("inspire_roles", [])
            for role in inspire_roles:
                if role not in creators_roles:
                    contributors.append(author)

        return self._transform_creatibutors(contributors, ctx)
