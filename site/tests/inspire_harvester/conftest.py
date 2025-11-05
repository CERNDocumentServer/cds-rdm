# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures and plugins for the API application."""

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
    """Transformed via InspireJsonTransformer record with no files."""
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
                    "resource_type": {"id": "publication-other"},
                }
            ],
        },
        "files": {"enabled": False},
        "parent": {"access": {"owned_by": {"user": 2}}},
        "access": {"record": "public", "files": "public"},
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
