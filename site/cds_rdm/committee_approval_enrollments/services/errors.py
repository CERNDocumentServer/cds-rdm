# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities errors."""

from invenio_i18n import lazy_gettext as _


class CommitteeApprovalEnrollmentNotFoundError(Exception):
    """Entry does not exist."""

    description = _("Committee approval community not found.")


class CommitteeApprovalEnrollmentAlreadyExistsError(Exception):
    """Community is already enrolled."""

    description = _("This community is already enrolled in the approval workflow.")
