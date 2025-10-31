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


def existing_cds_migrated_record(running_app):
    """Create a test record."""
