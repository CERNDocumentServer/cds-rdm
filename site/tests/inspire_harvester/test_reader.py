# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""ISNPIRE harvester reader tests."""

from unittest.mock import Mock, patch

import pytest
from invenio_vocabularies.datastreams.errors import ReaderError

from cds_rdm.inspire_harvester.reader import InspireHTTPReader


def test_reader_response_400(running_app):
    """Test InspireHTTPReader response error."""

    with patch("requests.get") as mock_get:
        # Create a mock response object
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_get.return_value = mock_response

        reader = InspireHTTPReader(inspire_id="1234")

        with pytest.raises(ReaderError) as e:
            list(reader.read())
        assert str(e.value).startswith(
            "Error occurred while getting JSON data from INSPIRE. See URL: https://inspirehep.net/api/literature?q=_oai.sets%3AForCDS+AND+document_type%3Athesis+AND+id%3A1234. Error message: "
        )


def test_reader_empty_results(running_app, caplog):
    """Test InspireHTTPReader no results found."""
    no_results_json = {"hits": {"hits": [], "total": 0}, "links": {}}

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = no_results_json

        mock_get.return_value = mock_response

        reader = InspireHTTPReader(inspire_id="1234")
        list(reader.read())

        # check that stuff was logged
        assert "No results found when querying INSPIRE. See URL: " in caplog.text


def test_reader_success(running_app):
    """Test InspireHTTPReader successfull response."""

    reader = InspireHTTPReader(since="2024-11-11", until="2025-01-11")

    for data in reader.read():
        assert len(data) > 0
        assert "metadata" in data
        assert "id" in data
        assert "links" in data
