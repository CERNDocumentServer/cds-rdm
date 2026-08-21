# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Reader component."""
from urllib.parse import urlencode

import requests
from flask import current_app
from invenio_vocabularies.datastreams.errors import ReaderError
from invenio_vocabularies.datastreams.readers import BaseReader

from cds_rdm.inspire_harvester.transform.resource_types import ALL_DOCUMENT_TYPES

INSPIRE_LITERATURE_API = "https://inspirehep.net/api/literature"


class InspireHTTPReader(BaseReader):
    """INSPIRE HTTP Reader."""

    def __init__(
        self,
        origin=None,
        mode="r",
        since=None,
        until=None,
        on_date=None,
        inspire_id=None,
        document_type=ALL_DOCUMENT_TYPES,
        *args,
        **kwargs,
    ):
        """Constructor."""
        self._since = since
        self._until = until
        self._on_date = on_date
        self._inspire_id = inspire_id
        self._document_type = document_type

        super().__init__(origin, mode, *args, **kwargs)

    def _build_url(self, q, **params):
        """Build an INSPIRE literature search URL."""
        query_params = {"q": q, **params}
        return f"{INSPIRE_LITERATURE_API}?{urlencode(query_params)}"

    def _get_json(self, url, headers):
        """Fetch JSON from INSPIRE or raise ReaderError."""
        current_app.logger.info(f"Querying URL: {url}.")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            error_message = (
                f"Error occurred while getting JSON data from INSPIRE. "
                f"See URL: {url}. Error message: {response.text}. "
                f"Status code: {response.status_code}"
            )
            current_app.logger.error(error_message)
            raise ReaderError(error_message)
        current_app.logger.debug("Request response is successful (200).")
        return response.json()

    def _scan_ids(self, q, headers):
        """Paginate an ID-only search and return IDs plus the reported total."""
        ids = set()
        url = self._build_url(q, fields="id", size=1000)
        reported_total = None

        while url:
            data = self._get_json(url, headers)
            if reported_total is None:
                reported_total = data["hits"]["total"]
            for hit in data["hits"]["hits"]:
                ids.add(str(hit["id"]))
            url = data.get("links", {}).get("next")

        return ids, reported_total

    def _iter(self, url, q, *args, **kwargs):
        """Yields HTTP response."""
        # header set to include additional data (external file URLs and more detailed metadata
        headers = {"Accept": "application/vnd+inspire.record.expanded+json"}
        initial_url = url
        seen_ids = set()
        expected_total = None
        had_another_page = False

        while url:  # Continue until there is no "next" link
            data = self._get_json(url, headers)
            total = data["hits"]["total"]
            hits = data["hits"]["hits"]

            if total == 0:
                current_app.logger.warning(
                    f"No results found when querying INSPIRE. See URL: {url}."
                )
            elif url == initial_url:
                expected_total = total
                current_app.logger.info(f"Records found: {total}.")

            for inspire_record in hits:
                record_id = str(inspire_record["id"])
                if record_id in seen_ids:
                    continue
                seen_ids.add(record_id)
                current_app.logger.debug(
                    f"Sending INSPIRE record #{record_id} to transformer."
                )
                yield inspire_record

            # Get the next page URL if available
            url = data.get("links", {}).get("next")
            # Remember if there was a second page.
            if url:
                had_another_page = True

        # If results moved while we were paging, we may have missed some records.
        # Skip this check for single-id jobs, or when everything fit on one page.
        if expected_total is None or self._inspire_id or not had_another_page:
            return

        # One ID-only scan, then harvest anything we missed.
        # Retry only if the scan collected fewer IDs than INSPIRE reported.
        all_ids, scan_total = self._scan_ids(q, headers)
        if scan_total is not None and len(all_ids) != scan_total:
            current_app.logger.warning(
                "ID scan found fewer INSPIRE records than reported. "
                f"| details: found={len(all_ids)}, reported={scan_total}"
            )
            retry_ids, _ = self._scan_ids(q, headers)
            if retry_ids != all_ids:
                current_app.logger.warning(
                    "INSPIRE ID scan shifted on retry. "
                    f"| details: first={len(all_ids)}, retry={len(retry_ids)}"
                )
                all_ids |= retry_ids

        # IDs we still need to fetch (in INSPIRE's list, not in what we already got).
        missing_ids = all_ids - seen_ids
        if not missing_ids:
            return

        current_app.logger.info(
            "Re-fetching missing INSPIRE records. "
            f"| details: missing={len(missing_ids)}, missing_ids={missing_ids}"
        )
        for record_id in missing_ids:
            data = self._get_json(
                self._build_url(f"{q} AND id:{record_id}"),
                headers,
            )
            for inspire_record in data["hits"]["hits"]:
                recovered_id = str(inspire_record["id"])
                seen_ids.add(recovered_id)
                current_app.logger.debug(
                    f"Sending INSPIRE record #{recovered_id} to transformer."
                )
                yield inspire_record

        still_missing = all_ids - seen_ids
        if still_missing:
            current_app.logger.warning(
                "After recovery, some INSPIRE records are still missing. "
                f"| details: missing_ids={still_missing}"
            )

    def read(self, item=None, *args, **kwargs):
        """Builds a query depending on the input data."""
        current_app.logger.info("Start reading data from INSPIRE.")

        # Fetch all document types marked for CDS via the OAI set
        oai_set = "ForCDS"

        q = f"_oai.sets:{oai_set}"
        if self._document_type and self._document_type != ALL_DOCUMENT_TYPES:
            q += f' AND document_type:"{self._document_type}"'

        document_type_scope = (
            "all document types"
            if not self._document_type or self._document_type == ALL_DOCUMENT_TYPES
            else self._document_type
        )
        current_app.logger.info(
            f"Harvesting INSPIRE scope: {document_type_scope}."
        )

        if self._inspire_id:
            # get by INSPIRE id
            current_app.logger.info(
                f"Fetching records by ID {self._inspire_id} from INSPIRE."
            )
            query_params = {"q": f"{q} AND id:{self._inspire_id}"}
        elif self._on_date:
            # get by the exact date
            current_app.logger.info(
                f"Fetching records by exact date {self._on_date} from INSPIRE."
            )
            query_params = {"q": f"{q} AND du:{self._on_date}"}
        elif self._until:
            # get by the date range
            current_app.logger.info(
                f"Fetching records by the date range {self._since} - {self._until} from INSPIRE."
            )
            query_params = {"q": f"{q} AND du >= {self._since} AND du <= {self._until}"}
        else:
            # get since specified date until now
            current_app.logger.info(
                f"Fetching records since {self._since} from INSPIRE."
            )
            query_params = {"q": f"{q} AND du >= {self._since}"}

        url = self._build_url(query_params["q"])

        current_app.logger.info(
            f"Resulting query: {query_params['q']}. URL for harvesting data from INSPIRE: {url}."
        )
        yield from self._iter(url=url, q=query_params["q"], *args, **kwargs)
