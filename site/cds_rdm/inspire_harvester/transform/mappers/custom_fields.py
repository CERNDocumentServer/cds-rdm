# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase
from cds_rdm.inspire_harvester.utils import get_vocabulary_exact


@dataclass(frozen=True)
class ImprintMapper(MapperBase):
    """Mapper for imprint custom fields."""

    id = "custom_fields.imprint:imprint"

    def map_value(self, src_record, ctx, logger):
        """Apply thesis field mapping."""
        src_metadata = src_record.get("metadata", {})
        imprints = src_metadata.get("imprints", [])
        imprint = imprints[0] if imprints else None

        place = imprint.get("place") if imprint else None
        editions = src_metadata.get("editions", [])
        if editions:
            ctx.errors.append(
                "Editions are not mapped. "
                f"| details: editions={editions}"
            )

        out = {}
        if place:
            out["place"] = place
        return out


@dataclass(frozen=True)
class CERNFieldsMapper(MapperBase):
    """Map CERN specific custom fields."""

    id = "custom_fields"

    def map_value(self, src_record, ctx, logger):
        """Apply mapping."""
        src_metadata = src_record.get("metadata", {})
        acc_exp_list = src_metadata.get("accelerator_experiments", [])
        _accelerators = []
        _experiments = []

        for item in acc_exp_list:
            accelerator = item.get("accelerator")
            experiment = item.get("experiment")
            institution = item.get("institution")

            if accelerator:
                if institution:
                    accelerator_term = f"{institution} {accelerator}"
                else:
                    accelerator_term = accelerator

                vocab_id = get_vocabulary_exact(
                    accelerator_term, "accelerators", ctx, logger
                )
                if vocab_id:
                    _accelerators.append({"id": vocab_id})

            if experiment:
                vocab_id = get_vocabulary_exact(
                    experiment, "experiments", ctx, logger
                )
                if vocab_id:
                    _experiments.append({"id": vocab_id})

        return {"cern:accelerators": _accelerators, "cern:experiments": _experiments}
