# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass
from datetime import date

import requests

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase
from cds_rdm.inspire_harvester.utils import get_vocabulary_exact


@dataclass(frozen=True)
class ImprintMapper(MapperBase):
    """Mapper for imprint custom fields."""

    id = "custom_fields.imprint:imprint"

    def map_value(self, src_record, ctx, logger):
        """Apply thesis field mapping."""
        src_metadata = src_record.get("metadata", {})
        imprints = src_metadata.get("imprints", [])
        imprint = imprints[0] if imprints else None

        place = imprint.get("place") if imprint else None
        editions = src_metadata.get("editions", [])
        if editions:
            ctx.errors.append(
                "Editions are not mapped. "
                f"| details: editions={editions}"
            )

        out = {}
        if place:
            out["place"] = place
        return out


@dataclass(frozen=True)
class CERNFieldsMapper(MapperBase):
    """Map CERN specific custom fields."""

    id = "custom_fields"

    def map_value(self, src_record, ctx, logger):
        """Apply mapping."""
        src_metadata = src_record.get("metadata", {})
        acc_exp_list = src_metadata.get("accelerator_experiments", [])
        _accelerators = []
        _experiments = []

        for item in acc_exp_list:
            accelerator = item.get("accelerator")
            experiment = item.get("experiment")
            institution = item.get("institution")

            if accelerator:
                if institution:
                    accelerator_term = f"{institution} {accelerator}"
                else:
                    accelerator_term = accelerator

                vocab_id = get_vocabulary_exact(
                    accelerator_term, "accelerators", ctx, logger
                )
                if vocab_id:
                    _accelerators.append({"id": vocab_id})

            if experiment:
                vocab_id = get_vocabulary_exact(
                    experiment, "experiments", ctx, logger
                )
                if vocab_id:
                    _experiments.append({"id": vocab_id})

        return {"cern:accelerators": _accelerators, "cern:experiments": _experiments}


def _format_meeting_dates(opening, closing):
    """Format ISO dates as e.g. ``22-26 September 2024``."""
    try:
        start = date.fromisoformat(opening) if opening else None
        end = date.fromisoformat(closing) if closing else None
    except ValueError:
        return opening or closing
    start = start or end
    end = end or start
    if not start:
        return None
    if start == end:
        return f"{start.day} {start:%B %Y}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day}-{end.day} {start:%B %Y}"
    if start.year == end.year:
        return f"{start.day} {start:%B} - {end.day} {end:%B %Y}"
    return f"{start.day} {start:%B %Y} - {end.day} {end:%B %Y}"


@dataclass(frozen=True)
class ConferenceMapper(MapperBase):
    """Mapper for conference information (``meeting:meeting``).

    INSPIRE literature records only carry ``cnum``, ``conf_acronym`` and a
    ``conference_record`` link in ``publication_info``, so the conference
    record is fetched to get the title, dates and place.
    """

    id = "custom_fields.meeting:meeting"
    timeout = 30

    def _fetch_conference(self, url, logger):
        """Fetch the INSPIRE conference metadata, ``None`` on failure."""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json().get("metadata", {})
        except (requests.RequestException, ValueError) as e:
            logger.warning(
                f"Could not fetch INSPIRE conference. | details: url={url}, error={e}"
            )
            return None

    def _map_conference(self, pub_info, logger):
        """Build a meeting entry out of one ``publication_info`` item."""
        cnum = pub_info.get("cnum")
        url = (pub_info.get("conference_record") or {}).get("$ref")
        conference = self._fetch_conference(url, logger) if url else None
        conference = conference or {}

        titles = conference.get("titles") or []
        acronyms = conference.get("acronyms") or []
        acronym = acronyms[0] if acronyms else pub_info.get("conf_acronym")
        title = titles[0].get("title") if titles else None
        title = title or acronym or cnum
        if not title:
            return None

        meeting = {"title": title}
        if acronym:
            meeting["acronym"] = acronym
        dates = _format_meeting_dates(
            conference.get("opening_date"), conference.get("closing_date")
        )
        if dates:
            meeting["dates"] = dates
        addresses = conference.get("addresses") or []
        if addresses:
            address = addresses[0]
            city = (address.get("cities") or [None])[0]
            place = ", ".join(p for p in (city, address.get("country")) if p)
            if place:
                meeting["place"] = place
        if cnum:
            meeting["identifiers"] = [{"identifier": cnum, "scheme": "inspire"}]
        return meeting

    def map_value(self, src_record, ctx, logger):
        """Map conferences found in ``publication_info``."""
        src_metadata = src_record.get("metadata", {})
        meetings = []
        seen = set()
        for pub_info in src_metadata.get("publication_info", []):
            cnum = pub_info.get("cnum")
            ref = (pub_info.get("conference_record") or {}).get("$ref")
            key = cnum or ref
            if not key or key in seen:
                continue
            seen.add(key)
            meeting = self._map_conference(pub_info, logger)
            if meeting:
                meetings.append(meeting)
        return meetings or None
