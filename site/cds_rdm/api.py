# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS overrides for the RDM Record and Draft API."""

from invenio_drafts_resources.records.systemfields import ParentField
from invenio_rdm_records.records.api import RDMDraft, RDMParent, RDMRecord
from invenio_records.dumpers import SearchDumper, SearchDumperExt


class _StripCommitteeApprovalDumperExt(SearchDumperExt):
    """Remove permission_flags.committee_approval from the parent's search document.

    committee_approval contains system-internal workflow state (report number, version
    pointers) that should only be read from the DB, not indexed in OpenSearch.
    Keeping it out of the index avoids uncontrolled dynamic mapping and prevents
    accidental exposure via search queries.
    """

    def dump(self, record, data):
        """Strip committee_approval from the dump."""
        try:
            data.get("permission_flags", {}).pop("committee_approval", None)
        except (AttributeError, TypeError):
            pass

    def load(self, data, record_cls):
        """Nothing to restore — field is DB-only."""
        pass


class CDSRDMParent(RDMParent):
    """CDS override of the RDM parent class."""

    dumper = SearchDumper(
        extensions=RDMParent.dumper._extensions + [_StripCommitteeApprovalDumperExt()]
    )


class CDSRDMRecord(RDMRecord):
    """CDS override of the RDM record class."""

    parent_record_cls = CDSRDMParent
    parent = ParentField(
        CDSRDMParent, create=False, soft_delete=False, hard_delete=False
    )


class CDSRDMDraft(RDMDraft):
    """CDS override of the RDM draft class."""

    parent_record_cls = CDSRDMParent
    parent = ParentField(
        CDSRDMParent, create=True, soft_delete=False, hard_delete=False
    )
