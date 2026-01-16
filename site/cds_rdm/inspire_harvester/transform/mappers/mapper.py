# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester context module."""

from abc import ABC, abstractmethod

from cds_rdm.inspire_harvester.transform.utils import set_path


class MapperBase(ABC):
    """Base class for metadata mappers."""

    id: str
    returns_patch: bool = False

    def apply(self, src_metadata, src_record, ctx, logger):
        """Apply the mapper to source metadata and return the result."""
        result = self.map_value(src_metadata, src_record, ctx, logger)
        if not result:
            return
        if self.returns_patch:
            if not isinstance(result, dict):
                raise TypeError(
                    f"{self.__class__.__name__} returns_patch=True but returned "
                    f"{type(result).__name__}, expected dict"
                )
            return result

        # Normal mode: wrap result under self.id
        return set_path(self.id, result)

    @abstractmethod
    def map_value(self, src, src_record, ctx, logger):
        """Return a value (not a patch). Return None for no-op."""
        raise NotImplementedError
