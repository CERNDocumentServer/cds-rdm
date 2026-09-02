# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2026 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS RDM request types."""

from .committee_approval import CommitteeApprovalRequest
from .community_inclusion import CDSCommunityInclusion
from .community_submission import CDSCommunitySubmission

__all__ = [
    "CommitteeApprovalRequest",
    "CDSCommunityInclusion",
    "CDSCommunitySubmission",
]
