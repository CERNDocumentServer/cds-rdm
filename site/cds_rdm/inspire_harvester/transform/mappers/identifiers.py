# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

import json
import re
from dataclasses import dataclass

from flask import current_app
from idutils.normalizers import normalize_isbn, normalize_urn
from idutils.validators import is_doi, is_urn

from cds_rdm import schemes
from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


def _coerce_urn(value):
    """Return a CDS-valid URN, or ``None`` if it cannot be safely corrected.

    INSPIRE sometimes stores URNs with an ``http(s)://`` prefix, e.g.
    ``http://nbnurn:nbn:de:...``. CDS validates with ``idutils.is_urn``, which
    requires the ``urn:`` scheme. Keep the value from that scheme onward only
    when the result is a valid URN.
    """
    if not isinstance(value, str):
        return None

    if is_urn(value):
        return normalize_urn(value)

    urn_idx = value.lower().find("urn:")
    candidate = value[urn_idx:] if urn_idx != -1 else None
    return normalize_urn(candidate) if candidate and is_urn(candidate) else None


def _related_identifier(schema, value, ctx):
    """Build a related-identifier dict, or ``None`` if the value is skipped.

    URN values are coerced/validated before they reach CDS record validation
    (same pattern as ISBN via ``normalize_isbn``).
    """
    if schema == "urn":
        original = value
        value = _coerce_urn(value)
        if not value:
            ctx.errors.append(f"Invalid URN. | details: value={original}")
            return None

    related = {
        "identifier": value,
        "scheme": schema,
        "relation_type": {"id": "isvariantformof"},
        "resource_type": {"id": "publication-other"},
    }
    if schema == "doi":
        related["relation_type"] = {"id": "isversionof"}
    return related


def _committee_approval_prefixes():
    """Return configured committee approval report-number prefixes."""
    communities = current_app.config.get("CDS_COMMITTEE_APPROVAL_COMMUNITIES", {})
    return {
        cfg.get("report_number", {}).get("prefix")
        for cfg in communities.values()
        if cfg.get("report_number", {}).get("prefix")
    }


def _is_approval_report_number(value):
    """Return True if value is a valid EP/approval report number.

    Requires both a configured committee prefix and a value accepted by the
    ``apprn`` scheme validator, so prefix look-alikes fall back to ``cdsrn``
    instead of failing record validation.
    """
    if not value:
        return False
    if not schemes.is_approval_report_number(value):
        return False
    # Prefix then a digit (the year), not another word like DRAFT.
    return any(
        re.match(rf"^{re.escape(prefix)}-\d", value)
        for prefix in _committee_approval_prefixes()
    )


@dataclass(frozen=True)
class DOIMapper(MapperBase):
    """Mapper for DOI identifiers."""

    id = "pids"

    def filter(self, doi):
        """Filter doi based on given criteria."""
        return True

    def map_value(self, src_record, ctx, logger):
        """Mapping of record dois.

        Prefer a CDS/DataCite-prefix DOI as the main PID. Any other DOIs become
        related identifiers (via ctx.extra_related_dois). Multiple non-CDS DOIs
        use the first as main and the rest as related (with a warning).
        """
        src_metadata = src_record.get("metadata", {})
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

        for doi in reversed(unique_dois):
            if not self.filter(doi):
                unique_dois.remove(doi)

        if not unique_dois:
            return None

        cds_dois = [
            d for d in unique_dois if d.get("value", "").startswith(DATACITE_PREFIX)
        ]
        other_dois = [
            d
            for d in unique_dois
            if not d.get("value", "").startswith(DATACITE_PREFIX)
        ]

        if len(cds_dois) > 1:
            ctx.errors.append(
                "More than 1 CDS DOI was found. "
                f"| details: dois={[d.get('value') for d in cds_dois]}"
            )
            return None

        if cds_dois:
            main = cds_dois[0]
            extras = other_dois
        elif other_dois:
            main = other_dois[0]
            extras = other_dois[1:]
            if extras:
                logger.warning(
                    "Multiple DOIs found; using one as main and others as "
                    "related identifiers. "
                    f"| details: main={main.get('value')}, "
                    f"related={[e.get('value') for e in extras]}"
                )
        else:
            return None

        doi = main.get("value")
        if not is_doi(doi):
            ctx.errors.append(f"DOI validation failed. | details: doi={doi}")
            return None

        for extra in extras:
            value = extra.get("value")
            if is_doi(value):
                ctx.extra_related_dois.append(value)
            else:
                ctx.errors.append(f"DOI validation failed. | details: doi={value}")

        mapped_doi = {"identifier": doi}
        if doi.startswith(DATACITE_PREFIX):
            mapped_doi["provider"] = "datacite"
        else:
            mapped_doi["provider"] = "external"
        return {"doi": mapped_doi}


@dataclass(frozen=True)
class IdentifiersMapper(MapperBase):
    """Mapper for record identifiers."""

    id = "metadata.identifiers"

    def map_value(self, src_record, ctx, logger):
        """Map identifiers from external system identifiers."""
        src_metadata = src_record.get("metadata", {})
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
                # dont self duplicate rdm identifier
                continue
            if schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                identifiers.append({"identifier": value, "scheme": schema})
            elif schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                continue
            else:
                # Stable group key — schema/value/id belong in details only if needed.
                # RelatedIdentifiersMapper skips these without re-logging.
                ctx.errors.append(
                    "Unexpected schema in external_system_identifiers. "
                    f"| details: schema={schema}, value={value}"
                )

        # Report numbers on the record itself:
        # - EP/approval numbers (configured prefixes) → apprn
        # - other CERN- report numbers → cdsrn
        for rn in src_metadata.get("report_numbers", []):
            report_number = rn.get("value")
            if not report_number:
                continue
            if _is_approval_report_number(report_number):
                identifiers.append({"identifier": report_number, "scheme": "apprn"})
            elif report_number.startswith("CERN-"):
                identifiers.append({"identifier": report_number, "scheme": "cdsrn"})

        unique_ids = [dict(t) for t in {tuple(sorted(d.items())) for d in identifiers}]
        return unique_ids


@dataclass(frozen=True)
class RelatedIdentifiersMapper(MapperBase):
    """Mapper for related identifiers."""

    id = "metadata.related_identifiers"

    def map_value(self, src_record, ctx, logger):
        """Mapping of alternate identifiers."""
        src_metadata = src_record.get("metadata", {})
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
                if schema == "arxiv":
                    value = f"arXiv:{value}"
                if schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                elif schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    related = _related_identifier(schema, value, ctx)
                    if related:
                        identifiers.append(related)
                else:
                    ctx.errors.append(
                        "Unexpected schema in persistent_identifiers. "
                        f"| details: schema={schema}, value={value}"
                    )

            # external_system_identifiers
            external_sys_ids = src_metadata.get("external_system_identifiers", [])
            for external_sys_id in external_sys_ids:
                schema = external_sys_id.get("schema").lower()
                value = external_sys_id.get("value")

                # these schemes are already in identifiers
                if schema in ["cdsrdm", "cds"]:
                    continue
                if schema in RDM_RECORDS_IDENTIFIERS_SCHEMES.keys():
                    continue
                elif schema in RDM_RECORDS_RELATED_IDENTIFIERS_SCHEMES.keys():
                    related = _related_identifier(schema, value, ctx)
                    if related:
                        identifiers.append(related)

                else:
                    # Already reported by IdentifiersMapper with a stable message.
                    continue

            # ISBNs
            isbns = src_metadata.get("isbns", [])
            for isbn in isbns:
                value = isbn.get("value")
                _isbn = normalize_isbn(value)
                if not _isbn:
                    ctx.errors.append(f"Invalid ISBN. | details: value={value}")
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
                        "resource_type": {"id": ctx.resource_type.value},
                    }
                )

            # Non-CERN- / non-approval report numbers stay related (scheme cdsrn).
            # CERN- cdsrn and apprn values are handled by IdentifiersMapper.
            report_numbers = src_metadata.get("report_numbers", [])
            for rn in report_numbers:
                report_number = rn.get("value")
                if (
                    not report_number
                    or report_number.startswith("CERN-")
                    or _is_approval_report_number(report_number)
                ):
                    continue
                identifiers.append(
                    {
                        "scheme": "cdsrn",
                        "identifier": report_number,
                        "relation_type": {"id": "isvariantformof"},
                        "resource_type": {"id": ctx.resource_type.value},
                    }
                )

            has_cds_doi = any(
                d.get("value", "").startswith(current_app.config["DATACITE_PREFIX"])
                for d in src_metadata.get("dois", [])
            )
            extra_rel = "isversionof" if has_cds_doi else "isvariantformof"
            for doi in ctx.extra_related_dois:
                identifiers.append(
                    {
                        "identifier": doi,
                        "scheme": "doi",
                        "relation_type": {"id": extra_rel},
                        "resource_type": {"id": "publication-other"},
                    }
                )

            identifiers.append(
                {
                    "scheme": "inspire",
                    "identifier": ctx.inspire_id,
                    "relation_type": {"id": "isvariantformof"},
                    "resource_type": {"id": ctx.resource_type.value},
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
            ctx.errors.append(f"Failed mapping identifiers. | details: error={e}")
            return None
