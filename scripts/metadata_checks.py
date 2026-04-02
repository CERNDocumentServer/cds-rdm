# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Script to create metadata checks for the CERN Research community.

Usage:

.. code-block:: shell

    invenio shell scripts/metadata_checks.py
"""

from copy import deepcopy

from invenio_checks.models import CheckConfig, Severity
from invenio_communities.proxies import current_communities
from invenio_db import db
from werkzeug.local import LocalProxy
from flask import current_app

community_service = LocalProxy(lambda: current_communities.service)


CERN_RESEARCH_RULES = {
    "rules": [
        {
            "id": "cern:programmes/thesis",
            "title": "CERN Programme participation",
            "message": "Thesis must specify the CERN Student programme participation",
            "description": "To submit your thesis you must select the CERN Programme which supported",
            "level": "error",
            "condition": {
                "type": "comparison",
                "left": {"type": "field", "path": "metadata.resource_type.id"},
                "operator": "==",
                "right": "publication-dissertation",  # Previously publication-thesis
            },
            "checks": [
                {
                    "type": "comparison",
                    "left": {
                        "type": "field",
                        "path": "custom_fields.cern:programmes",
                    },
                    "operator": "!=",
                    "right": "",
                }
            ],
        },
        {
            "id": "cern:doi/prefix-community",
            "title": "CERN DOI prefix required",
            "message": "Records with publisher CERN must use the CERN DOI prefix.",
            "description": "Ensures records published by CERN use the configured DataCite prefix when a DOI is provided.",
            "level": "error",
            "error_path": "pids.doi",
            "condition": {
                "type": "logical",
                "operator": "and",
                "expressions": [
                    {
                        "type": "comparison",
                        "left": {"type": "field", "path": "metadata.publisher"},
                        "operator": "==",
                        "right": "CERN",
                    },
                    {
                        "type": "comparison",
                        "left": {"type": "field", "path": "pids.doi.identifier"},
                        "operator": "!=",
                        "right": "",
                    },
                ],
            },
            "checks": [
                {
                    "type": "comparison",
                    "left": {"type": "field", "path": "pids.doi.identifier"},
                    "operator": "^=",
                    "right": current_app.config["DATACITE_PREFIX"],
                }
            ],
        },
    ]
}


CDS_CERN_SCIENTIFIC_COMMUNITY_ID = current_app.config[
    "CDS_CERN_SCIENTIFIC_COMMUNITY_ID"
]


def create_metadata_checks(community_id, checks):
    community = community_service.record_cls.pid.resolve(community_id)
    existing_check = CheckConfig.query.filter_by(
        community_id=community.id, check_id="metadata"
    ).one_or_none()
    if existing_check:  # If it exists, update it
        existing_check.params = checks
    else:  # ...create it
        check_config = CheckConfig(
            community_id=community.id,
            check_id="metadata",
            params=CERN_RESEARCH_RULES,
            severity=Severity.INFO,
            enabled=True,
        )
        db.session.add(check_config)
    db.session.commit()
    print(
        f"Metadata checks created/updated successfully for community {community.slug}."
    )


create_metadata_checks(CDS_CERN_SCIENTIFIC_COMMUNITY_ID, CERN_RESEARCH_RULES)
