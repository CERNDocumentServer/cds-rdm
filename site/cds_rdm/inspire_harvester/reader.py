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
# Cap re-harvest passes so a shifting result set cannot loop forever.
MAX_HARVEST_PASSES = 3


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

    def _iter(self, url, *args, **kwargs):
        """Yields HTTP response."""
        # header set to include additional data (external file URLs and more detailed metadata
        headers = {"Accept": "application/vnd+inspire.record.expanded+json"}
        # Three nested loops:
        # - outer: re-harvest from the start when we got fewer records than INSPIRE
        #   reported (capped at MAX_HARVEST_PASSES)
        # - middle (page_url): walk INSPIRE pagination (next page links)
        # - inner (hits): yield each record on the current page
        # seen_ids tracks ids already yielded in this run so retries do not send
        # the same record twice. first_pass makes us retry at least once. if a
        # later pass adds nothing new (new_in_pass == 0), harvesting stops.
        harvest_url = url
        seen_ids = set()
        first_pass = True

        for pass_number in range(1, MAX_HARVEST_PASSES + 1):
            page_url = harvest_url
            reported_total = None
            new_in_pass = 0

            while page_url:
                data = self._get_json(page_url, headers)
                total = data["hits"]["total"]
                hits = data["hits"]["hits"]

                if reported_total is None:
                    reported_total = total
                    if total == 0:
                        current_app.logger.warning(
                            f"No results found when querying INSPIRE. See URL: {page_url}."
                        )
                    else:
                        current_app.logger.info(f"Records found: {total}.")

                for inspire_record in hits:
                    record_id = str(inspire_record["id"])
                    if record_id in seen_ids:
                        continue
                    seen_ids.add(record_id)
                    new_in_pass += 1
                    current_app.logger.debug(
                        f"Sending INSPIRE record #{record_id} to transformer."
                    )
                    yield inspire_record

                page_url = data.get("links", {}).get("next")

            if len(seen_ids) == reported_total:
                return

            if not first_pass and new_in_pass == 0:
                current_app.logger.warning(
                    "Harvest retry added no new INSPIRE records; stopping. "
                    f"| details: harvested={len(seen_ids)}, reported={reported_total}"
                )
                return

            if pass_number == MAX_HARVEST_PASSES:
                current_app.logger.warning(
                    "Harvest still short of INSPIRE total after max retries; stopping. "
                    f"| details: harvested={len(seen_ids)}, reported={reported_total}, "
                    f"max_passes={MAX_HARVEST_PASSES}"
                )
                return

            first_pass = False
            current_app.logger.info(
                "Harvested fewer INSPIRE records than reported; harvesting again. "
                f"| details: harvested={len(seen_ids)}, reported={reported_total}, "
                f"pass={pass_number}/{MAX_HARVEST_PASSES}"
            )

    def read(self, item=None, *args, **kwargs):
        """Builds a query depending on the input data."""
        current_app.logger.info("Start reading data from INSPIRE.")

        # Fetch all document types marked for CDS via the OAI set
        oai_set = "ForCDS"

        # INSPIRE's search defaults to the Literature collection, which hides
        # records that only live in "CDS Hidden", so ask for those explicitly.
        q = f'(_collections:"CDS Hidden" OR _oai.sets:{oai_set})'
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
        yield from self._iter(url=url, *args, **kwargs)
