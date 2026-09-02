# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-specific Community Inclusion request."""

from invenio_rdm_records.checks import requests as checks_request


class CDSCommunityInclusion(checks_request.CommunityInclusion):
    """CommunityInclusion with narrowed permissions."""

    needs_context = checks_request.CommunityInclusion.needs_context | {
        "record_permission": "view_request"
    }
