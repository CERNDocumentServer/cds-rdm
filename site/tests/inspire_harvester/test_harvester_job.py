# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""ISNPIRE harvester job tests."""
import json
from unittest.mock import Mock, patch

from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_vocabularies.datastreams import DataStreamFactory


def test_inspire_job(running_app):
    """Test the whole flow of an INSPIRE job."""
    ds_config = {
        "readers": [
            {
                "type": "inspire-http-reader",
                "args": {
                    "since": "2024-11-15",
                    "until": "2025-01-09",
                },
            },
        ],
        "transformers": [{"type": "inspire-json-transformer"}],
        "writers": [
            {
                "type": "async",
                "args": {
                    "writer": {
                        "type": "inspire-writer",
                    }
                },
            }
        ],
        "batch_size": 100,
        "write_many": True,
    }

    datastream = DataStreamFactory.create(
        readers_config=ds_config["readers"],
        transformers_config=ds_config["transformers"],
        writers_config=ds_config["writers"],
        batch_size=ds_config["batch_size"],
        write_many=ds_config["write_many"],
    )

    def mock_requests_get(url, headers={"Accept": "application/json"}, stream=True):
        with open(
            "data/inspire_response_15_records_page_1.json",
            "r",
        ) as f:
            mock_json_page1 = json.load(f)

        with open(
            "data/inspire_response_15_records_page_2.json",
            "r",
        ) as f:
            mock_json_page2 = json.load(f)

        mock_response = Mock()
        url_page_1 = "https://inspirehep.net/api/literature?q=_oai.sets%3AForCDS+AND+document_type%3Athesis+AND+du+%3E%3D+2024-11-15+AND+du+%3C%3D+2025-01-09"
        url_page_2 = "https://inspirehep.net/api/literature/?q=_oai.sets%3AForCDS+AND+document_type%3Athesis+AND+du+%3E%3D+2024-11-15+AND+du+%3C%3D+2025-01-09&size=10&page=2"
        url_file = "https://inspirehep.net/files/4550b6ee36afc3fdedc08d0423375ab4"

        mock_response.status_code = 200
        if url == url_page_1:
            mock_response.json.return_value = mock_json_page1
        elif url == url_page_2:
            mock_response.json.return_value = mock_json_page2
        elif url == url_file:
            with open("data/inspire_file.bin", "rb") as f:
                mock_content = f.read()
                mock_response.content = mock_content

        return mock_response

    with patch(
        "cds_rdm.inspire_harvester.reader.requests.get", side_effect=mock_requests_get
    ):
        result = datastream.process()

        for _, entry in enumerate(result):
            created_record = entry.entry
            assert "metadata" in created_record
            assert (
                created_record["metadata"]["resource_type"]["id"]
                == "publication-thesis"
            )

        created_records = current_rdm_records_service.search(system_identity)
        assert len(created_records) == 15
