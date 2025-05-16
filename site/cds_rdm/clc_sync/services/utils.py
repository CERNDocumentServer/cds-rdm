# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLCSync utils."""
import requests
from flask import current_app


def clc_import(record_data):
    """Import a record to CLC."""
    clc_url = current_app.config["CLC_URL_SYNC"]
    clc_token = current_app.config["CDS_ILS_IMPORTER_API_KEY"]
    clc_payload = {
        "data": record_data,
        "mode": "IMPORT",
    }

    headers = {
        "Content-Type": "application/vnd.inveniordm.v1+json",
        "Accept": "application/vnd.inveniordm.v1+json",
        "Authorization": f"Bearer {clc_token}",
    }
    response = requests.post(
        f"{clc_url}api/import", json=clc_payload, headers=headers, verify=False
    )
    response.raise_for_status()
    return response.json()
