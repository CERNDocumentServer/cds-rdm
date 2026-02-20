# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Field update strategies for core metadata fields."""

import copy

import dateparser

from cds_rdm.inspire_harvester.update.engine import UpdateConflict, UpdateResult
from cds_rdm.inspire_harvester.update.field import FieldUpdateBase
from cds_rdm.inspire_harvester.utils import get_path, set_path


class PublicationDateUpdate(FieldUpdateBase):
    """
    Update publication_date only if incoming value is more accurate.

    Accuracy (granularity):
        YYYY < YYYY-MM < YYYY-MM-DD

    Uses dateutil for parsing and validation.
    """

    def __init__(self,
                 conflict_on_year_mismatch: bool = True,
                 conflict_on_same_year_mismatch: bool = True):
        """Initialize with flags controlling conflict reporting for date discrepancies."""
        self.conflict_on_year_mismatch = conflict_on_year_mismatch
        self.conflict_on_same_year_mismatch = conflict_on_same_year_mismatch

    def _granularity(self, s: str) -> int:
        """Return 1,2,3 for year, month, day granularity."""
        s = s.strip()
        if len(s) == 4:
            return 1
        if len(s) == 7:
            return 2
        if len(s) == 10:
            return 3
        raise ValueError("Invalid publication_date format")

    def _parse(self, s: str):
        """Parse and validate date string."""
        # dateutil parses partial dates but fills missing parts with defaults.
        dt = dateparser.parse(s)
        return dt, self._granularity(s)

    def update(self, current, incoming, path, ctx):
        """Update publication_date only when the incoming value is more granular."""
        cur_v = get_path(current, path)
        inc_v = get_path(incoming, path)

        if inc_v is None:
            return UpdateResult(updated=current)

        # Parse both
        try:
            cur_dt, cur_g = self._parse(str(cur_v))
        except ValueError:
            return UpdateResult(
                updated=current,
                conflicts=[UpdateConflict(
                    path=path,
                    kind="invalid_date",
                    message="Current publication_date invalid",
                    current=cur_v,
                )],
            )

        try:
            inc_dt, inc_g = self._parse(str(inc_v))
        except ValueError:
            return UpdateResult(
                updated=current,
                conflicts=[UpdateConflict(
                    path=path,
                    kind="invalid_date",
                    message="Incoming publication_date invalid",
                    incoming=inc_v,
                )],
            )

        # Year mismatch
        if cur_dt.year != inc_dt.year:
            if self.conflict_on_year_mismatch:
                return UpdateResult(
                    updated=current,
                    conflicts=[UpdateConflict(
                        path=path,
                        kind="year_mismatch",
                        message="Incoming publication_date year differs",
                        current=cur_v,
                        incoming=inc_v,
                    )],
                )
            return UpdateResult(updated=current)

        # Same year but contradicts known month/day
        if inc_g >= 2 and cur_g >= 2 and inc_dt.month != cur_dt.month:
            if self.conflict_on_same_year_mismatch:
                return UpdateResult(
                    updated=current,
                    conflicts=[UpdateConflict(
                        path=path,
                        kind="month_mismatch",
                        message="Incoming publication_date contradicts current month",
                        current=cur_v,
                        incoming=inc_v,
                    )],
                )
            return UpdateResult(updated=current)

        if inc_g == 3 and cur_g == 3 and inc_dt.day != cur_dt.day:
            if self.conflict_on_same_year_mismatch:
                return UpdateResult(
                    updated=current,
                    conflicts=[UpdateConflict(
                        path=path,
                        kind="day_mismatch",
                        message="Incoming publication_date contradicts current day",
                        current=cur_v,
                        incoming=inc_v,
                    )],
                )
            return UpdateResult(updated=current)

        # Incoming more accurate → update
        if inc_g > cur_g:
            updated = copy.deepcopy(current)
            set_path(updated, path, inc_v.strip())
            return UpdateResult(
                updated=updated,
                audit=[f"{path}: updated to more accurate value ({cur_v} → {inc_v})"],
            )

        # Otherwise keep current
        return UpdateResult(updated=current)