# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester module."""

from dataclasses import dataclass

from cds_rdm.inspire_harvester.transform.mappers.config import (
    INSPIRE_CORRECTION_MATERIALS,
)
from cds_rdm.inspire_harvester.transform.mappers.mapper import MapperBase


def get_correction_material(item, filename=""):
    """Return the correction material of a DOI or document, if any.

    INSPIRE sets ``material`` on some documents, but often only the filename
    (e.g. ``erratum.pdf``) tells it apart.
    """
    material = (item.get("material") or "").lower()
    if material in INSPIRE_CORRECTION_MATERIALS:
        return material
    name = filename.lower()
    return next((q for q in INSPIRE_CORRECTION_MATERIALS if q in name), None)


@dataclass(frozen=True)
class FilesMapper(MapperBase):
    """Mapper for files."""

    id = "files"

    def filter(self, file):
        """Filters files based on given criteria."""
        return True

    def map_value(self, src_record, ctx, logger):
        """Map files from INSPIRE documents to RDM files."""
        src_metadata = src_record.get("metadata", {})
        logger.debug(f"Starting _transform_files")

        rdm_files_entries = {}
        inspire_files = src_metadata.get("documents", [])
        logger.debug(f" Processing {len(inspire_files)} documents")

        for file in inspire_files:
            if self.filter(file):
                logger.debug(f"Processing file: {file.get('filename', 'unknown')}")
                filename = file["filename"]
                source = file.get("source")
                url = file["url"]
                if not filename.lower().endswith(".pdf"):
                    # INSPIRE only exposes pdfs for us
                    filename = f"{filename}.pdf"

                # link to files directly from arxiv
                if "key" not in file and source != "arxiv":
                    ctx.errors.append(
                        "File is missing a checksum. "
                        f"| details: filename={filename}, source={source}"
                    )
                    return {}

                src_checksum = f"md5:{file['key']}" if "key" in file else None
                try:
                    file_details = {
                        "checksum": src_checksum,
                        "key": filename,
                        "access": {"hidden": False},
                        "source_url": file["url"],
                    }

                    rdm_files_entries[filename] = file_details
                    correction = get_correction_material(file, filename)
                    logger.info(f"File mapped: {file_details}. File name: {filename}.")

                    file_metadata = {"source": source, "source_url": file["url"]}
                    file_description = file.get("description")
                    file_original_url = file.get("original_url")
                    if file_description:
                        file_metadata["description"] = file_description
                    if file_original_url:
                        file_metadata["original_url"] = file_original_url

                    if correction:
                        # Displayed title
                        file_metadata["description"] = correction

                    if file_metadata:
                        rdm_files_entries[filename]["metadata"] = file_metadata

                except Exception as e:
                    ctx.errors.append(
                        "Error occurred while mapping files. "
                        f"| details: filename={filename}, error={e}"
                    )

        logger.debug(f"Files transformation completed with {len(ctx.errors)} errors")
        if rdm_files_entries:
            return {
                "enabled": True,
                "entries": rdm_files_entries,
            }

        return {"enabled": False}
