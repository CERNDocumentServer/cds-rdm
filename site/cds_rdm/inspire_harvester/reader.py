# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Reader component."""
from urllib.parse import urlencode

import requests
from invenio_vocabularies.datastreams.errors import ReaderError


class InspireHTTPReader:
    """INSPIRE HTTP Reader."""

    def __init__(
        self,
        since=None,
        until=None,
        on=None,
        inspire_id=None,
    ):
        """Constructor."""
        self._since = since
        self._until = until
        self._on = on
        self._inspire_id = inspire_id

    def _iter(self, url, *args, **kwargs):
        """Yields HTTP response."""
        headers = {"Accept": "application/json"}

        while url:  # Continue until there is no "next" link
            response = requests.get(url, headers=headers)
            data = response.json()

            if response.status_code == 200:
                if (
                    data["hits"]["total"] == 0
                ):  # TODO make it a warning or info when we have proper logging
                    raise ReaderError(
                        f"No results found when querying INSPIRE. See URL: {url}."
                    )

                yield response.content
            else:
                raise ReaderError(
                    f"Error occurred while getting JSON data from INSPIRE. Error message: {response.text}. See URL: {url}."
                )

            # Get the next page URL if available
            url = data.get("links", {}).get("next")

    def read(self, item=None, *args, **kwargs):
        """Builds a query depending on the input data."""
        document_type = "thesis"
        oai_set = "ForCDS"

        if self._inspire_id:
            # get by INSPIRE id
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND id:{self._inspire_id}"
            }
        elif self._on:
            # get by the exact date
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du:{self._on}"
            }
        elif self._until:
            # get by the date range
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du >= {self._since} AND du <= {self._until}"
            }
        else:
            # get since specified date until now
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du >= {self._since}"
            }

        base_url = "https://inspirehep.net/api/literature"
        encoded_query = urlencode(query_params)
        url = f"{base_url}?{encoded_query}"

        yield from self._iter(url=url, *args, **kwargs)
