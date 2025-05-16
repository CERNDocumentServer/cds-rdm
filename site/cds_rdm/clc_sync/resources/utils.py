# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM CLC Sync Resource utils."""

from flask import g

from cds_rdm.clc_sync.proxies import current_clc_sync_service


def get_clc_sync_entry(record):
    """Get the CLC sync entry for the record.

    :param record: The record to get the CLC sync entry for.
    :return: The CLC sync entry.
    """
    try:
        clc_sync_entry = current_clc_sync_service.read(
            g.identity,
            record.get("parent", {}).get(
                "id",
            ),
        ).to_dict()
        return clc_sync_entry
    except Exception as e:
        return None
