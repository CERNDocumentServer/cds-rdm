# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Reader component."""
from urllib.parse import urlencode

import requests
from flask import current_app
from invenio_vocabularies.datastreams.errors import ReaderError
from invenio_vocabularies.datastreams.readers import BaseReader


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
        *args,
        **kwargs,
    ):
        """Constructor."""
        self._since = since
        self._until = until
        self._on_date = on_date
        self._inspire_id = inspire_id

        super().__init__(origin, mode, *args, **kwargs)

    def _iter(self, url, *args, **kwargs):
        """Yields HTTP response."""
        headers = {"Accept": "application/json"}

        current_app.logger.info(
            "Sending the request and iterating through the resulting pages."
        )

        while url:  # Continue until there is no "next" link
            current_app.logger.info(f"Querying URL: {url}.")
            response = requests.get(url, headers=headers)
            data = response.json()
            if response.status_code == 200:
                current_app.logger.info("Request response is successful (200).")
                if data["hits"]["total"] == 0:
                    current_app.logger.warning(
                        f"No results found when querying INSPIRE. See URL: {url}."
                    )

                for inspire_record in data["hits"]["hits"]:
                    current_app.logger.debug(
                        f"Sending INSPIRE record to transformer. Record details: {inspire_record}."
                    )
                    yield inspire_record
            else:
                current_app.logger.error(
                    f"Request response is not successful. Status code: {response.status_code}."
                )
                raise ReaderError(
                    f"Error occurred while getting JSON data from INSPIRE. Error message: {response.text}. See URL: {url}."
                )

            # Get the next page URL if available
            url = data.get("links", {}).get("next")

    def read(self, item=None, *args, **kwargs):
        """Builds a query depending on the input data."""
        current_app.logger.info("Start reading data from INSPIRE.")

        document_type = "thesis"
        oai_set = "ForCDS"

        if self._inspire_id:
            # get by INSPIRE id
            current_app.logger.debug(
                "INSPIRE ID provided. Building query params for request to INSPIRE based on that."
            )
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND id:{self._inspire_id}"
            }
        elif self._on_date:
            # get by the exact date
            current_app.logger.debug(
                "Exact date 'On' provided. Building query params for request to INSPIRE based on "
                "that."
            )
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du:{self._on_date}"
            }
        elif self._until:
            # get by the date range
            current_app.logger.debug(
                "'Until' date provided. Building query params for request to INSPIRE based on that."
            )
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du >= {self._since} AND du <= {self._until}"
            }
        else:
            # get since specified date until now
            current_app.logger.debug(
                "'Since' date provided. Building query params for request to INSPIRE based on that."
            )
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du >= {self._since}"
            }

        current_app.logger.info(f"Resulting query: {query_params['q']}.")
        base_url = "https://inspirehep.net/api/literature"
        encoded_query = urlencode(query_params)
        url = f"{base_url}?{encoded_query}"

        current_app.logger.info(
            f"Resulting URL for harvesting data from INSPIRE: {url}."
        )
        yield from self._iter(url=url, *args, **kwargs)
