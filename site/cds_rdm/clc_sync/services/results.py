# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""CDS-RDM CLC sync results module."""


from invenio_records_resources.services.records.results import RecordItem, RecordList


class SyncItem(RecordItem):
    """Single banner result."""

    def __init__(
        self,
        service,
        identity,
        banner,
        links_tpl=None,
        errors=None,
        schema=None,
    ):
        """Constructor."""
        super().__init__(service, identity, banner, errors, links_tpl, schema)

    @property
    def data(self):
        """Property to get the banner."""
        if self._data:
            return self._data

        self._data = self._schema.dump(
            self._obj,
            context={
                "identity": self._identity,
                "record": self._record,
            },
        )

        return self._data


class SyncList(RecordList):
    """List result."""

    @property
    def total(self):
        """Get total number of hits."""
        if self._results:
            return self._results.get("total", 0)
        return 0

    @property
    def hits(self):
        """Iterator over the hits."""
        for hit in self._results["hits"]:
            projection = self._schema.dump(
                hit,
                context={
                    "identity": self._identity,
                    "record": hit,
                },
            )

            yield projection
