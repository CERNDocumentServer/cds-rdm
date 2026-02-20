# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester context module."""

from abc import ABC, abstractmethod


class FieldUpdateBase(ABC):
    """Base class for metadata mappers."""

    def apply(self, current_record, incoming_update, path, ctx):
        """Apply the mapper to source metadata and return the result."""
        return self.update(current_record, incoming_update, path, ctx)

    @abstractmethod
    def update(self, current_record, incoming_update, path, ctx):
        """Return a value (not a patch). Return None for no-op."""
        raise NotImplementedError
