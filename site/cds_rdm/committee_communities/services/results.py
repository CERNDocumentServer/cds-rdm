# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it
# under the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Committee approval communities results."""

from invenio_records_resources.services.records.results import RecordItem, RecordList


class CommitteeCommunityItem(RecordItem):
    """Single entry result."""

    @property
    def data(self):
        """Dump the entry."""
        if self._data is None:
            self._data = self._schema.dump(
                self._record, context={"identity": self._identity}
            )
            if self._links_tpl:
                # the admin UI uses ``links.self`` for edit/delete actions
                self._data["links"] = self.links
        return self._data


class CommitteeCommunityList(RecordList):
    """List result."""

    @property
    def total(self):
        """Total number of hits."""
        return self._results.get("total", 0)

    @property
    def aggregations(self):
        """Facet buckets."""
        return self._results.get("aggregations")

    @property
    def hits(self):
        """Iterate over the hits."""
        for hit in self._results["hits"]:
            projection = self._schema.dump(hit, context={"identity": self._identity})
            if self._links_item_tpl:
                projection["links"] = self._links_item_tpl.expand(self._identity, hit)
            yield projection
