# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from idutils.normalizers import normalize_isbn

from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase
from cds_rdm.inspire_harvester.transform.utils import search_vocabulary


@dataclass(frozen=True)
class ImprintMapper(MapperBase):
    """Mapper for imprint custom fields."""

    id = "custom_fields.imprint:imprint"

    def map_value(self, src_metadata, ctx, logger):
        """Apply thesis field mapping."""
        imprints = src_metadata.get("imprints", [])
        imprint = imprints[0] if imprints else None
        isbns = src_metadata.get("isbns", [])

        online_isbns = []
        for isbn in isbns:
            value = isbn.get("value")
            valid_isbn = normalize_isbn(value)
            if not valid_isbn:
                ctx.errors.append(f"Invalid ISBN '{value}'.")
            else:
                if isbn.get("medium") == "online":
                    online_isbns.append(valid_isbn)

        if len(online_isbns) > 1:
            ctx.errors.append(f"More than one electronic ISBN found: {online_isbns}.")

        place = imprint.get("place") if imprint else None

        # TODO this is true only for thesis
        isbn = online_isbns[0] if online_isbns else None
        out = {}
        if place:
            out["place"] = place
        if isbn:
            out["isbn"] = isbn
        return out


@dataclass(frozen=True)
class CERNFieldsMapper(MapperBase):
    """Map CERN specific custom fields."""

    id = "custom_fields"

    def map_value(self, src_metadata, ctx, logger):
        """Apply mapping."""
        acc_exp_list = src_metadata.get("accelerator_experiments", [])
        _accelerators = []
        _experiments = []
        for item in acc_exp_list:
            accelerator = item.get("accelerator")
            experiment = item.get("experiment")
            institution = item.get("institution")

            if accelerator:
                logger.debug(
                    f"Searching vocabulary 'accelerator' for term: '{accelerator}'"
                )
                accelerator = f"{institution} {accelerator}"
                result = search_vocabulary(accelerator, "accelerators", ctx, logger)
                if result.total == 1:
                    logger.info(f"Found accelerator '{accelerator}'")
                    hit = list(result.hits)[0]
                    _accelerators.append({"id": hit["id"]})
                else:
                    logger.warning(
                        f"Accelerator '{accelerator}' not found for INSPIRE#{ctx.inspire_id}"
                    )

            if experiment:
                logger.debug(
                    f"Searching vocabulary 'experiments' for term: '{experiment}'"
                )
                result = search_vocabulary(experiment, "experiments", ctx, logger)
                if result.total == 1:
                    logger.info(f"Found experiment '{experiment}'")
                    hit = list(result.hits)[0]
                    _experiments.append({"id": hit["id"]})
                else:
                    logger.warning(
                        f"Accelerator '{accelerator}' not found for INSPIRE#{ctx.inspire_id}"
                    )

        return {"cern:accelerators": _accelerators, "cern:experiments": _experiments}
