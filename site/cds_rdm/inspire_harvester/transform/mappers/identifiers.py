# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

import json
from dataclasses import dataclass

from flask import current_app
from idutils.normalizers import normalize_isbn
from idutils.validators import is_doi

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


@dataclass(frozen=True)
class DOIMapper(MapperBase):
    """Mapper for DOI identifiers."""

    id = "pids"

    def map_value(self, src_metadata, src_record, ctx, logger):
        """Mapping of record dois."""
        DATACITE_PREFIX = current_app.config["DATACITE_PREFIX"]
        dois = src_metadata.get("dois", [])

        if not dois:
            return {}

        seen = set()
        unique_dois = []
        for d in dois:
            if d["value"] not in seen:
                unique_dois.append(d)
                seen.add(d["value"])

        if len(unique_dois) > 1:
            ctx.errors.append(f"More than 1 DOI was found in INSPIRE#{ctx.inspire_id}.")
            return None
        elif len(unique_dois) == 0:
            return None
        else:
            doi = unique_dois[0].get("value")
            if is_doi(doi):
                mapped_doi = {
                    "identifier": doi,
                }
                if doi.startswith(DATACITE_PREFIX):
                    mapped_doi["provider"] = "datacite"
                else:
                    mapped_doi["provider"] = "external"
                return {"doi": mapped_doi}
            else:
                ctx.errors.append(
                    f"DOI validation failed. DOI#{doi}. INSPIRE#{ctx.inspire_id}."
                )
                return None


@dataclass(frozen=True)
class IdentifiersMapper(MapperBase):
    """Mapper for record identifiers."""

    id = "metadata.identifiers"

    def map_value(self, src_metadata, src_record, ctx, logger):
        """Map identifiers from external system identifiers."""
        identifiers = []
        RDM_RECORDS_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_IDENTIFIERS_SCHEMES"
        ]
        RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES"
        ]

        external_sys_ids = src_metadata.get("external_system_identifiers", [])

        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema").lower()
            value = external_sys_id.get("value")
            if schema == "cdsrdm":
                schema = "cds"
            if schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                identifiers.append({"identifier": value, "scheme": schema})
            elif schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                continue
            else:
                ctx.errors.append(
                    f"Unexpected schema found in external_system_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {ctx.inspire_id}."
                )
        unique_ids = [dict(t) for t in {tuple(sorted(d.items())) for d in identifiers}]
        return unique_ids


@dataclass(frozen=True)
class RelatedIdentifiersMapper(MapperBase):
    """Mapper for related identifiers."""

    id = "metadata.related_identifiers"

    def map_value(self, src_metadata, src_record, ctx, logger):
        """Mapping of alternate identifiers."""
        identifiers = []
        RDM_RECORDS_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_IDENTIFIERS_SCHEMES"
        ]
        RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES = current_app.config[
            "RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES"
        ]
        CDS_INSPIRE_IDS_SCHEMES_MAPPING = current_app.config[
            "CDS_INSPIRE_IDS_SCHEMES_MAPPING"
        ]

        try:
            # persistent_identifiers
            persistent_ids = src_metadata.get("persistent_identifiers", [])
            for persistent_id in persistent_ids:
                schema = persistent_id.get("schema").lower()
                schema = CDS_INSPIRE_IDS_SCHEMES_MAPPING.get(schema, schema)
                value = persistent_id.get("value")
                if schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    new_id = {
                        "identifier": value,
                        "scheme": schema,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                    if schema == "doi":
                        new_id["relation_type"] = {"id": "isversionof"}
                    identifiers.append(new_id)
                elif schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                else:
                    ctx.errors.append(
                        f"Unexpected schema found in persistent_identifiers. Schema: {schema}, value: {value}. INSPIRE#: {ctx.inspire_id}."
                    )

            # external_system_identifiers
            external_sys_ids = src_metadata.get("external_system_identifiers", [])
            for external_sys_id in external_sys_ids:
                schema = external_sys_id.get("schema").lower()
                value = external_sys_id.get("value")
                if schema == "cdsrdm":
                    continue
                if schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    new_id = {
                        "identifier": value,
                        "scheme": schema,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                    if schema == "doi":
                        new_id["relation_type"] = {"id": "isversionof"}
                    identifiers.append(new_id)
                elif schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                else:
                    ctx.errors.append(
                        f"Unexpected schema found in external_system_identifiers. Schema: {schema}, value: {value}. INSPIRE record id: {ctx.inspire_id}."
                    )

            # ISBNs
            isbns = src_metadata.get("isbns", [])
            for isbn in isbns:
                value = isbn.get("value")
                _isbn = normalize_isbn(value)
                if not _isbn:
                    ctx.errors.append(f"Invalid ISBN '{value}'.")
                else:
                    identifiers.append(
                        {
                            "identifier": _isbn,
                            "scheme": "isbn",
                            "relation_type": {"id": "isvariantformof"},
                            "resource_type": {"id": "publication-book"},
                        }
                    )

            arxiv_ids = src_metadata.get("arxiv_eprints", [])
            for arxiv_id in arxiv_ids:
                identifiers.append(
                    {
                        "scheme": "arxiv",
                        "identifier": f"arXiv:{arxiv_id['value']}",
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": "publication-other"},
                    }
                )

            identifiers.append(
                {
                    "scheme": "inspire",
                    "identifier": ctx.inspire_id,
                    "relation_type": {"id": "isvariantformof"},
                    "resource_type": {"id": "publication-other"},
                }
            )

            seen = set()
            unique_ids = []
            for d in identifiers:
                s = json.dumps(d, sort_keys=True)
                if s not in seen:
                    seen.add(s)
                    unique_ids.append(d)
            return unique_ids
        except Exception as e:
            ctx.errors.append(
                f"Failed mapping identifiers. INSPIRE#: {ctx.inspire_id}. Error: {e}."
            )
            return None
