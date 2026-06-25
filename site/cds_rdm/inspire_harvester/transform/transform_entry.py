# -*- coding: utf-8 -*-
#
# Copyright (C) 2025-2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Transform RDM entry."""
from copy import deepcopy

from flask import current_app
from invenio_access.permissions import system_user_id

from cds_rdm.inspire_harvester.logger import Logger
from cds_rdm.inspire_harvester.transform.config import mapper_policy
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.resource_types import ResourceTypeDetector
from cds_rdm.inspire_harvester.transform.splitter import InspireVersionSplitter
from cds_rdm.inspire_harvester.utils import assert_unique_ids, deep_merge_all


class RDMEntry:
    """Building of CDS-RDM entry record."""

    def __init__(self, inspire_record):
        """Initializes the RDM entry."""
        self.inspire_record = inspire_record
        self.inspire_metadata = inspire_record["metadata"]
        self.transformer = Inspire2RDM(self.inspire_record)
        self.cds_id = self.transformer.cds_id
        self.splitter = InspireVersionSplitter(
            self.inspire_record, self.transformer.ctx, self.cds_id
        )
        self.errors = []

    def _id(self):
        return self.inspire_record["id"]

    def _record(self):
        """Transformation of metadata."""
        record = self.transformer.transform_record()
        self.errors.extend(self.transformer.ctx.errors)
        return record

    def _versions(self):
        versions = self.splitter.split()
        return versions

    def _files(self, record):
        """Transformation of files."""
        return record.get("files")

    def _parent(self):
        """Record parent minimal values."""
        parent = {
            "access": {
                "owned_by": {
                    "user": system_user_id,
                }
            }
        }
        return parent

    def _access(self):
        """Record access minimal values."""
        access = {
            "record": "public",
            "files": "public",
        }
        return access

    def build(self):
        """Perform building of CDS-RDM entry record."""
        inspire_id = self.inspire_record.get("id")
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting build of CDS-RDM entry record"
        )

        inspire_files = self.inspire_metadata.get("documents", [])
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Found {len(inspire_files)} files in INSPIRE record"
        )

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Starting record metadata transformation"
        )
        record = self._record()
        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Record metadata transformation completed"
        )

        rdm_record = {
            "id": self._id(),
            "metadata": record["metadata"],
            "custom_fields": record["custom_fields"],
            "files": self._files(record),
            "parent": self._parent(),
            "access": self._access(),
        }

        if record.get("pids"):
            rdm_record["pids"] = record["pids"]

        current_app.logger.debug(
            f"[inspire_id={inspire_id}] Building CDS-RDM entry record finished. "
        )

        versions = self._versions()
        return rdm_record, versions, self.cds_id, self.errors


class Inspire2RDM:
    """INSPIRE to CDS-RDM record mapping."""

    def __init__(
        self, inspire_record, detector_cls=ResourceTypeDetector, policy=mapper_policy
    ):
        """Initializes the Inspire2RDM class."""
        self.policy = policy

        self.inspire_record = inspire_record
        self.inspire_original_metadata = inspire_record["metadata"]
        self.inspire_id = self.inspire_record.get("id")
        self.cds_id = self._get_cds_id(self.inspire_original_metadata)

        self.logger = Logger(inspire_id=self.inspire_id)
        rt, errors = detector_cls(self.inspire_id, self.logger).detect(
            self.inspire_original_metadata
        )
        self.ctx = MetadataSerializationContext(
            resource_type=rt, inspire_id=self.inspire_id, cds_rdm_id=self.cds_id
        )

        for error in errors:
            self.ctx.errors.append(error)

        self.resource_type = rt

        # pre-clean data and update the record with cleaned metadata
        self.inspire_metadata = self._clean_data(self.inspire_original_metadata)
        self.inspire_record["metadata"] = self.inspire_metadata

    def _clean_data(self, src_metadata):
        """Cleans the input data."""
        metadata = deepcopy(src_metadata)
        self._clean_identifiers(metadata)
        return metadata

    def _get_cds_id(self, src_metadata):
        """Get CDS ID from INSPIRE metadata."""
        external_sys_ids = src_metadata.get("external_system_identifiers", [])
        cds_id = None
        seen_cds_ids = []
        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema")
            if schema.upper() in ["CDS", "CDSRDM"]:
                seen_cds_ids.append(external_sys_id)

        if seen_cds_ids:
            rdm_id = next(
                (
                    identifier
                    for identifier in seen_cds_ids
                    if identifier["schema"] == "CDSRDM"
                ),
                {},
            ).get("value")
            if rdm_id:
                # prefer rdm ID
                return rdm_id
            cds_id = next(
                (
                    identifier
                    for identifier in seen_cds_ids
                    if identifier["schema"] == "CDS"
                ),
                {},
            ).get("value")

        return cds_id

    def _clean_identifiers(self, metadata):
        IDENTIFIERS_SCHEMES_TO_DROP = [
            "SPIRES",
            "HAL",
            "OSTI",
            "SLAC",
            "PROQUEST",
        ]
        external_sys_ids = metadata.get("external_system_identifiers", [])
        persistent_ids = metadata.get("persistent_identifiers", [])

        cleaned_external_sys_ids = []
        cleaned_persistent_ids = []

        for external_sys_id in external_sys_ids:
            schema = external_sys_id.get("schema")
            if schema.upper() not in IDENTIFIERS_SCHEMES_TO_DROP:
                cleaned_external_sys_ids.append(external_sys_id)
        for persistent_id in persistent_ids:
            schema = persistent_id.get("schema")

            if schema.upper() not in IDENTIFIERS_SCHEMES_TO_DROP:
                cleaned_persistent_ids.append(persistent_id)

        metadata["external_system_identifiers"] = cleaned_external_sys_ids
        metadata["persistent_identifiers"] = cleaned_persistent_ids

    def transform_record(self):
        """Perform record transformation."""
        self.logger.debug("Start transform_record")
        self.logger.info(f"Building mapper policy for {self.ctx.resource_type}")
        mappers = self.policy.build_for(self.ctx.resource_type)
        assert_unique_ids(mappers)
        patches = [m.apply(self.inspire_record, self.ctx, self.logger) for m in mappers]

        out_record = deep_merge_all(patches)
        return out_record
