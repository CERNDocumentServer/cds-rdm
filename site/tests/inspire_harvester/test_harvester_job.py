# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""ISNPIRE harvester job tests."""
import json
from pathlib import Path

import pytest
from invenio_access.permissions import system_identity
from invenio_jobs.errors import TaskExecutionPartialError
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_rdm_records.records.api import RDMRecord

from .utils import mock_requests_get, run_harvester_mock

DATA_DIR = Path(__file__).parent / "data"

expected_result_1 = {
    "metadata": {
        "resource_type": {
            "id": "publication-dissertation",
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
        'contributors': [
            {
                'affiliations': [
                    {
                        'name': 'Budapest, Tech. U.',
                    },
                ],
                'person_or_org': {
                    'family_name': 'DiCaprio',
                    'given_name': 'Leonardo',
                    'name': 'DiCaprio, Leonardo',
                    'type': 'personal',
                },
                'role': {
                    'id': 'supervisor',
                    'title': {
                        'en': 'Supervisor',
                    },
                },
            },
            {
                'affiliations': [
                    {
                        'name': 'Wigner RCP, Budapest',
                    },
                ],
                'person_or_org': {
                    'family_name': 'Bullock',
                    'given_name': 'Sandra',
                    'name': 'Bullock, Sandra',
                    'type': 'personal',
                },
                'role': {
                    'id': 'supervisor',
                    'title': {
                        'en': 'Supervisor',
                    },
                },
            },
        ],
        "title": "Fragmentation through Heavy and Light-flavor Measurements with the LHC ALICE Experiment",
        "publication_date": "2024",
        "languages": [{"id": "eng", "title": {"en": "English", "da": "Engelsk"}}],
        "identifiers": [
            {"identifier": "2918369", "scheme": "cds"},
        ],
        "related_identifiers": [
            {
                "identifier": "2840463",
                "relation_type": {
                    "id": "isvariantformof",
                    "title": {
                        "en": "is variant of",
                    },
                },
                "resource_type": {
                    "id": "publication-other",
                    "title": {
                        "de": "Abschlussarbeit",
                        "en": "Other",
                    },
                },
                "scheme": "inspire",
            },
        ],
        "description": "A few microseconds after the Big Bang, the universe was filled with an extremely hot and dense mixture of particles moving at near light speed.",
    },
    "custom_fields": {'cern:accelerators': [
        {
            'id': 'CERN LHC',
            'title': {
                'en': 'CERN LHC',
            },
        },
    ],
        'cern:experiments': [
            {
                'id': 'ALICE',
                'title': {
                    'en': 'ALICE',
                },
            },
        ],
        'thesis:thesis': {

            'type': 'PhD',
            'university': 'Budapest, Tech. U.',
        }, },
}

expected_result_2 = {
    "metadata": {
        "resource_type": {
            "id": "publication-dissertation",
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
        'contributors': [
            {
                'person_or_org': {
                    'family_name': 'Parker',
                    'given_name': 'Sylvia',
                    'name': 'Parker, Sylvia',
                    'type': 'personal',
                },
                'role': {
                    'id': 'supervisor',
                    'title': {
                        'en': 'Supervisor',
                    },
                },
            },
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
            {"identifier": "2152014", "scheme": "cds"},
        ],
        "related_identifiers": [
            {
                "identifier": "1452604",
                "relation_type": {
                    "id": "isvariantformof",
                    "title": {
                        "en": "is variant of",
                    },
                },
                "resource_type": {
                    "id": "publication-other",
                    "title": {
                        "de": "Abschlussarbeit",
                        "en": "Other",
                    },
                },
                "scheme": "inspire",
            },
        ],
        "description": "The AMS-02 experiment is a particle detector installed on the International Space Station (ISS) since May 2011, which measures the characteristics of the cosmic rays to bring answers to the problematics risen by the astroparticle physics since a few decades, in particular the study of dark matter and the search of antimatter. The phenomenological aspects of the physics of cosmic rays are reviewed in a first part.",
    },
    "custom_fields": {
        'thesis:thesis': {
            'type': 'PhD',
            'university': 'U. Grenoble Alpes',
        },
    },
}

expected_result_3 = {
    "metadata": {
        "resource_type": {
            "id": "publication-dissertation",
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
        'contributors': [
            {
                'affiliations': [
                    {
                        'name': 'San Luis Potosi U.',
                    },
                ],
                'person_or_org': {
                    'family_name': 'Termopolis',
                    'given_name': 'Mia',
                    'name': 'Termopolis, Mia',
                    'type': 'personal',
                },
                'role': {
                    'id': 'supervisor',
                    'title': {
                        'en': 'Supervisor',
                    },
                },
            },
        ],
        "title": "Medición del tiempo de vida del K+ en el experimento NA62",
        "publication_date": "2024-05",
        "languages": [{"id": "spa", "title": {"en": "Spanish"}}],
        "identifiers": [
            {"identifier": "2918367", "scheme": "cds"},
        ],
        "related_identifiers": [
            {
                "identifier": "2802969",
                "relation_type": {
                    "id": "isvariantformof",
                    "title": {
                        "en": "is variant of",
                    },
                },
                "resource_type": {
                    "id": "publication-other",
                    "title": {
                        "de": "Abschlussarbeit",
                        "en": "Other",
                    },
                },
                "scheme": "inspire",
            },
        ],
        "description": "In the present study the possibility of measuring the lifetime of the positively charged Kaon , K+, is investigated , by using data and framework produced by the experiment NA62 of the European Organization for Nuclear Research (CERN).",
    },
    "custom_fields": {"thesis:thesis": {'type': 'Bachelor',
                                        'university': 'San Luis Potosi U.', }},
}


def tranformation(record_pid, expected_result):
    record = current_rdm_records_service.read(system_identity, record_pid)
    record_dict = record.to_dict()
    assert expected_result["metadata"] == record_dict["metadata"]
    assert expected_result["custom_fields"] == record_dict["custom_fields"]


def test_inspire_job(running_app, scientific_community):
    """Test the whole flow of an INSPIRE job."""
    ds_config = {
        "config": {
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
    }

    def mock_requests_get_pagination(
            url, headers={"Accept": "application/vnd+inspire.record.expanded+json"},
            stream=True
    ):
        page_1_file = DATA_DIR / "inspire_response_15_records_page_1.json"
        page_2_file = DATA_DIR / "inspire_response_15_records_page_2.json"
        url_page_1 = "https://inspirehep.net/api/literature?q=_oai.sets%3AForCDS+AND+du+%3E%3D+2024-11-15+AND+du+%3C%3D+2025-01-09"
        url_page_2 = "https://inspirehep.net/api/literature/?q=_oai.sets%3AForCDS+AND+du+%3E%3D+2024-11-15+AND+du+%3C%3D+2025-01-09&size=10&page=2"

        filepath = ""
        if url == url_page_1:
            filepath = page_1_file
        elif url == url_page_2:
            filepath = page_2_file

        content = ""
        if filepath:
            with open(
                    filepath,
                    "r",
            ) as f:
                content = json.load(f)

        return mock_requests_get(url, mock_content=content)

    with pytest.raises(TaskExecutionPartialError) as e:
        run_harvester_mock(ds_config, mock_requests_get_pagination)

    RDMRecord.index.refresh()
    created_records = current_rdm_records_service.search(system_identity)

    assert created_records.total == 9

    created_record1 = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.related_identifiers.identifier:2840463"})

    created_record2 = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.related_identifiers.identifier:1452604"})

    created_record3 = current_rdm_records_service.search(
        system_identity,
        params={"q": f"metadata.related_identifiers.identifier:2802969"})

    tranformation(created_record1.to_dict()["hits"]["hits"][0]["id"], expected_result_1)

    tranformation(created_record2.to_dict()["hits"]["hits"][0]["id"], expected_result_2)

    tranformation(created_record3.to_dict()["hits"]["hits"][0]["id"], expected_result_3)
