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
from invenio_rdm_records.records.api import RDMRecord
from invenio_vocabularies.datastreams import DataStreamFactory

expected_result_1 = {
    "metadata": {
        "resource_type": {
            "id": "publication-thesis",
            "title": {"en": "Thesis", "de": "Abschlussarbeit"},
        },
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Reynolds, Ryan",
                    "given_name": "Ryan",
                    "family_name": "Reynolds",
                }
            }
        ],
        "title": "Unbinned amplitude analysis of the $B^0 \\rightarrow K^{*0}\\mu^+\\mu^-$ decay using an amplitude ansatz method at the LHCb experiment",
        "additional_titles": [
            {
                "title": "Unbinned amplitude analysis of the $B^0 \\rightarrow K^{*0}\\mu^+\\mu^-$ decay using an amplitude ansatz method at the LHCb experiment",
                "type": {
                    "id": "alternative-title",
                    "title": {"en": "Alternative title"},
                },
            }
        ],
        "publication_date": "2024",
        "identifiers": [{"identifier": "2850153", "scheme": "inspire"}],
        "description": "An amplitude analysis of the B0 → K∗0μ+μ− decay is presented in this thesis.",
        "additional_descriptions": [
            {
                "description": "An amplitude analysis of the B0 → K∗0μ+μ− decay is presented in this thesis.",
                "type": {"id": "abstract", "title": {"en": "Abstract"}},
            }
        ],
    },
    "custom_fields": {},
}

expected_result_2 = {
    "metadata": {
        "resource_type": {
            "id": "publication-thesis",
            "title": {"en": "Thesis", "de": "Abschlussarbeit"},
        },
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Portman, Natalie",
                    "given_name": "Natalie",
                    "family_name": "Portman",
                }
            }
        ],
        "title": "Fragmentation through Heavy and Light-flavor Measurements with the LHC ALICE Experiment",
        "publication_date": "2024",
        "identifiers": [{"identifier": "2840463", "scheme": "inspire"}],
        "description": "A few microseconds after the Big Bang, the universe was filled with an extremely hot and dense mixture of particles moving at near light speed.",
    },
    "custom_fields": {},
}

expected_result_3 = {
    "metadata": {
        "resource_type": {
            "id": "publication-thesis",
            "title": {"en": "Thesis", "de": "Abschlussarbeit"},
        },
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "name": "Cruise, Tom",
                    "given_name": "Tom",
                    "family_name": "Cruise",
                }
            }
        ],
        "title": "Probing the Top-Yukawa Coupling by Searching for Associated Higgs Boson Production with a Single Top Quark at the CMS Experiment",
        "publication_date": "2016",
        "identifiers": [{"identifier": "1647487", "scheme": "inspire"}],
        "description": "In this thesis the associated production of a single top quark with a Higgs boson is studied.",
    },
    "custom_fields": {},
}

expected_result_4 = {
    "metadata": {},
    "custom_fields": {},
}


def tranformation(record_pid, expected_result):
    record = current_rdm_records_service.read(system_identity, record_pid)
    record_dict = record.to_dict()
    assert expected_result["metadata"] == record_dict["metadata"]
    assert expected_result["custom_fields"] == record_dict["custom_fields"]


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
            "tests/inspire_harvester/data/inspire_response_15_records_page_1.json",
            "r",
        ) as f:
            mock_json_page1 = json.load(f)

        with open(
            "tests/inspire_harvester/data/inspire_response_15_records_page_2.json",
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
            with open("tests/inspire_harvester/data/inspire_file.bin", "rb") as f:
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

        # check if tasks still running
        from celery import current_app

        tasks = current_app.control.inspect()
        while True:
            if not tasks.scheduled():
                break

        RDMRecord.index.refresh()
        created_records = current_rdm_records_service.search(system_identity)

        # 10 records with files, 5 without
        assert created_records.total == 10
        tranformation(
            created_records.to_dict()["hits"]["hits"][0]["id"], expected_result_1
        )

        tranformation(
            created_records.to_dict()["hits"]["hits"][1]["id"], expected_result_2
        )

        tranformation(
            created_records.to_dict()["hits"]["hits"][2]["id"], expected_result_3
        )
