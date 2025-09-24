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
                    "name": "Portman, Natalie",
                    "given_name": "Natalie",
                    "family_name": "Portman",
                },
                "affiliations": [{"name": "Budapest, Tech. U."}],
            }
        ],
        "title": "Fragmentation through Heavy and Light-flavor Measurements with the LHC ALICE Experiment",
        "publication_date": "2024",
        "languages": [{"id": "eng", "title": {"en": "English", "da": "Engelsk"}}],
        "identifiers": [
            {"identifier": "2840463", "scheme": "inspire"},
            {"identifier": "2918369", "scheme": "lcds"},
            {
                "identifier": "https://wigner.hu/~vertesi/publ/24-PhD-Thesis-VargaZ.pdf",
                "scheme": "url",
            },
        ],
        "description": "A few microseconds after the Big Bang, the universe was filled with an extremely hot and dense mixture of particles moving at near light speed.",
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
                    "name": "Chalamet, Timothee",
                    "given_name": "Timothee",
                    "family_name": "Chalamet",
                },
                "affiliations": [{"name": "U. Grenoble Alpes"}],
            }
        ],
        "title": "Performance of the Electromagnetic Calorimeter of AMS-02 on the International Space Station ans measurement of the positronic fraction in the 1.5 – 350 GeV energy range",
        "publication_date": "2014",
        "subjects": [
            {"subject": "Multivariate analysis"},
            {"subject": "Proton rejection"},
            {"subject": "Positronic fraction"},
            {"subject": "Astroparticles"},
            {"subject": "Alpha Magnetic Spectrometer"},
            {"subject": "thesis"},
            {"subject": "calorimeter: electromagnetic"},
            {"subject": "performance"},
            {"subject": "AMS"},
            {"subject": "charged particle: irradiation"},
            {"subject": "attenuation"},
            {"subject": "data analysis method"},
        ],
        "identifiers": [
            {"identifier": "1452604", "scheme": "inspire"},
            {"identifier": "2152014", "scheme": "lcds"},
            {
                "identifier": "https://tel.archives-ouvertes.fr/tel-01155127/",
                "scheme": "url",
            },
            {
                "identifier": "https://tel.archives-ouvertes.fr/tel-01155127",
                "scheme": "url",
            },
        ],
        "description": "The AMS-02 experiment is a particle detector installed on the International Space Station (ISS) since May 2011, which measures the characteristics of the cosmic rays to bring answers to the problematics risen by the astroparticle physics since a few decades, in particular the study of dark matter and the search of antimatter. The phenomenological aspects of the physics of cosmic rays are reviewed in a first part.",
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
                    "name": "Maradona Franco, Diego Armando",
                    "given_name": "Diego Armando",
                    "family_name": "Maradona Franco",
                },
                "affiliations": [{"name": "San Luis Potosi U."}],
            }
        ],
        "title": "Medición del tiempo de vida del K+ en el experimento NA62",
        "publication_date": "2024-05",
        "languages": [{"id": "spa", "title": {"en": "Spanish"}}],
        "identifiers": [
            {"identifier": "2802969", "scheme": "inspire"},
            {"identifier": "2918367", "scheme": "lcds"},
            {
                "identifier": "https://www.ifisica.uaslp.mx/~jurgen/AkbarEmmanuelDiazRodarte-Lic.pdf",
                "scheme": "url",
            },
            {
                "identifier": "https://www.ifisica.uaslp.mx/~jurgen/Theses.html",
                "scheme": "url",
            },
        ],
        "description": "In the present study the possibility of measuring the lifetime of the positively charged Kaon , K+, is investigated , by using data and framework produced by the experiment NA62 of the European Organization for Nuclear Research (CERN).",
    },
    "custom_fields": {},
}


def tranformation(record_pid, expected_result):
    record = current_rdm_records_service.read(system_identity, record_pid)
    record_dict = record.to_dict()
    assert expected_result["metadata"] == record_dict["metadata"]
    assert expected_result["custom_fields"] == record_dict["custom_fields"]


def test_inspire_job(running_app, scientific_community):
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
            with open(
                "tests/inspire_harvester/data/inspire_file.bin",
                "rb",
            ) as f:
                mock_content = f.read()
                mock_response.content = mock_content

        return mock_response

    with patch(
        "cds_rdm.inspire_harvester.reader.requests.get", side_effect=mock_requests_get
    ):
        result = datastream.process()
        for _, entry in enumerate(result):
            created_record = entry.entry

            if created_record:
                assert "metadata" in created_record
                assert (
                    created_record["metadata"]["resource_type"]["id"]
                    == "publication-thesis"
                )
            else:
                assert created_record == None  # for metadata-only records

        # check if tasks still running
        from celery import current_app

        tasks = current_app.control.inspect()
        while True:
            if not tasks.scheduled():
                break

        RDMRecord.index.refresh()
        created_records = current_rdm_records_service.search(system_identity)

        assert created_records.total == 4
        tranformation(
            created_records.to_dict()["hits"]["hits"][0]["id"], expected_result_1
        )

        tranformation(
            created_records.to_dict()["hits"]["hits"][1]["id"], expected_result_2
        )

        tranformation(
            created_records.to_dict()["hits"]["hits"][2]["id"], expected_result_3
        )
