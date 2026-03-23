# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures and plugins for the API application."""
from unittest.mock import Mock

import pytest


@pytest.fixture()
def datastream_config():
    """Create config fixture."""
    return {
        "config": {
            "readers": [
                {
                    "type": "inspire-http-reader",
                    "args": {
                        "inspire_id": "3065322",
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


@pytest.fixture(scope="function")
def transformed_record_no_files():
    """Transform via InspireJsonTransformer record with no files."""
    return {
        "id": "1695540",
        "metadata": {
            "title": "Helium II heat transfer in LHC magnets",
            "additional_titles": [
                {"title": "Polyimide cable insulation", "type": {"id": "subtitle"}}
            ],
            "publication_date": "2017",
            "resource_type": {"id": "publication-dissertation"},
            "creators": [
                {"person_or_org": {"type": "personal", "family_name": "Hanks, Tom"}},
                {"person_or_org": {"type": "personal", "family_name": "Potter, Harry"}},
                {"person_or_org": {"type": "personal", "family_name": "Weasley, Ron"}},
            ],
            "related_identifiers": [
                {
                    "identifier": "1695540",
                    "scheme": "inspire",
                    "relation_type": {"id": "isversionof"},
                    "resource_type": {"id": "publication-dissertation"},
                }
            ],
        },
        "files": {"enabled": False},
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
        "_inspire_ctx": {"cds_id": None, "versions": []},
    }


@pytest.fixture()
def minimal_record():
    """Minimal record data as dict coming from the external world."""
    return {
        "pids": {},
        "access": {
            "record": "public",
            "files": "public",
        },
        "files": {
            "enabled": False,  # Most tests don't care about files
        },
        "metadata": {
            "creators": [
                {
                    "person_or_org": {
                        "family_name": "Brown",
                        "given_name": "Troy",
                        "type": "personal",
                    }
                },
                {
                    "person_or_org": {
                        "name": "Troy Inc.",
                        "type": "organizational",
                    },
                },
            ],
            "publication_date": "2020-06-01",
            # because DATACITE_ENABLED is True, this field is required
            "publisher": "Acme Inc",
            "resource_type": {"id": "image-photo"},
            "title": "A Romans story",
        },
    }


@pytest.fixture()
def existing_fcc_record():
    """Create an existing record."""
    return {
        "pids": {
            "doi": {
                "identifier": "10.17181/fp18d-jc149",
                "provider": "datacite",
                "client": "datacite",
            },
            "oai": {"identifier": "oai:cds-rdm.com:fp18d-jc149", "provider": "oai"},
        },
        "metadata": {
            "resource_type": {
                "id": "publication",
            },
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "Ahmis, Yasmine",
                        "given_name": "Yasmine",
                        "family_name": "Ahmis",
                        "identifiers": [
                            {"identifier": "0000-0003-4282-1512", "scheme": "orcid"}
                        ],
                    },
                    "affiliations": [
                        {"name": "CERN"},
                        {"name": "Universit\u00e9 Paris-Saclay"},
                    ],
                },
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "Kenzie, Matthew",
                        "given_name": "Matthew",
                        "family_name": "Kenzie",
                        "identifiers": [
                            {"identifier": "0000-0001-7910-4109", "scheme": "orcid"}
                        ],
                    },
                    "role": {
                        "id": "contactperson",
                    },
                    "affiliations": [{"name": "University of Cambridge"}],
                },
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "Reboud, Meril",
                        "given_name": "Meril",
                        "family_name": "Reboud",
                        "identifiers": [
                            {"identifier": "0000-0001-6033-3606", "scheme": "orcid"}
                        ],
                    },
                    "affiliations": [{"name": "Durham University"}],
                },
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "Wiederhold, Aidan",
                        "given_name": "Aidan",
                        "family_name": "Wiederhold",
                        "identifiers": [
                            {"identifier": "0000-0002-1023-1086", "scheme": "orcid"}
                        ],
                    },
                    "affiliations": [{"name": "University of Warwick"}],
                },
            ],
            "title": "Prospects of searches for $b\\to s\\nu\\bar{\\nu}$ decays at FCC-ee",
            "publisher": "CERN",
            "publication_date": "2024-01-24",
            "identifiers": [],  # lrecid is 2882312 but we will not know this on the first harvest record already exists in new cds
            "related_identifiers": [],
            "rights": [
                {
                    "id": "cc-by-4.0",
                }
            ],
            "description": "<p>We investigate the physics reach and potential for the study of various decays involving a \\bsnunu transition at the Future Circular Collider running electron-positron collisions at the $Z$-pole (FCC-ee).</p><p>Signal and background candidates, which involve inclusive $Z$ contributions from $b\\bar{b}$, $c\\bar{c}$ and $uds$ final states, are simulated for a proposed multi-purpose detector. Signal candidates are selected using two Boosted Decision Tree algorithms.</p><p>We determine expected relative sensitivities of $0.53\\%$, $1.20\\%$, $3.37\\%$ and $9.86\\%$ for the branching fractions of the \\BdKstNuNu, \\BsPhiNuNu, \\BdKSNuNu and \\LbLzNuNu decays, respectively. &nbsp;</p><p>In addition, we investigate the impact of detector design choices related to particle-identification and vertex resolution.</p><p>The phenomenological impact of such measurements on the extraction of Standard Model and new physics parameters is also studied.</p>",
        },
        "custom_fields": {},
        "access": {
            "record": "public",
            "files": "public",
            "embargo": {"active": False, "reason": None},
            "status": "open",
        },
    }
