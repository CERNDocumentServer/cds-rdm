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
        #
        super().__init__(origin, mode, *args, **kwargs)

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

                for inspire_record in data["hits"]["hits"]:
                    yield inspire_record
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
        elif self._on_date:
            # get by the exact date
            query_params = {
                "q": f"_oai.sets:{oai_set} AND document_type:{document_type} AND du:{self._on_date}"
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
