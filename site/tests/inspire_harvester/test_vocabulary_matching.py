# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Tests for vocabulary exact matching functionality."""
from cds_rdm.inspire_harvester.logger import Logger
from cds_rdm.inspire_harvester.transform.context import MetadataSerializationContext
from cds_rdm.inspire_harvester.transform.mappers.custom_fields import CERNFieldsMapper
from cds_rdm.inspire_harvester.transform.resource_types import ResourceType
from cds_rdm.inspire_harvester.utils import get_vocabulary_exact


def test_get_vocabulary_exact_found(running_app):
    """Test get_vocabulary_exact with a term that exists in vocabulary."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    result = get_vocabulary_exact("CERN LHC", "accelerators", ctx, logger)

    assert result == "CERN LHC"
    assert len(ctx.errors) == 0


def test_get_vocabulary_exact_not_found(running_app):
    """Test get_vocabulary_exact with a term not in vocabulary."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    result = get_vocabulary_exact("UNKNOWN", "accelerators", ctx, logger)

    assert result is None
    assert len(ctx.errors) == 0


def test_get_vocabulary_exact_normalizes_case(running_app):
    """Test get_vocabulary_exact normalizes case before lookup."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    result = get_vocabulary_exact("alice", "experiments", ctx, logger)

    assert result == "ALICE"
    assert len(ctx.errors) == 0


def test_get_vocabulary_exact_normalizes_hyphens(running_app):
    """Test get_vocabulary_exact strips hyphens before lookup."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    # "NA-62" normalizes to "NA62" which exists in vocabulary
    result = get_vocabulary_exact("NA-62", "experiments", ctx, logger)

    assert result == "NA62"
    assert len(ctx.errors) == 0


def test_get_vocabulary_exact_empty_term(running_app):
    """Test get_vocabulary_exact with empty term."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    result = get_vocabulary_exact("", "accelerators", ctx, logger)

    assert result is None
    assert len(ctx.errors) == 0


def test_get_vocabulary_exact_none_term(running_app):
    """Test get_vocabulary_exact with None term."""
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")

    result = get_vocabulary_exact(None, "accelerators", ctx, logger)

    assert result is None
    assert len(ctx.errors) == 0


def test_cern_fields_mapper_accelerator_found(running_app):
    """Test CERNFieldsMapper with accelerator that exists in vocabulary."""
    src_metadata = {
        "accelerator_experiments": [
            {"accelerator": "LHC", "institution": "CERN"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CERNFieldsMapper()
    src_record = {"metadata": src_metadata, "created": "2023-01-01"}

    result = mapper.map_value(src_record, ctx, logger)

    assert len(result["cern:accelerators"]) == 1
    assert result["cern:accelerators"][0]["id"] == "CERN LHC"
    assert len(ctx.errors) == 0


def test_cern_fields_mapper_accelerator_not_found(running_app):
    """Test CERNFieldsMapper with accelerator not in vocabulary."""
    src_metadata = {
        "accelerator_experiments": [
            {"accelerator": "UNKNOWN"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CERNFieldsMapper()
    src_record = {"metadata": src_metadata, "created": "2023-01-01"}

    result = mapper.map_value(src_record, ctx, logger)

    assert len(result["cern:accelerators"]) == 0
    assert len(ctx.errors) == 0


def test_cern_fields_mapper_experiment_found(running_app):
    """Test CERNFieldsMapper with experiment that exists in vocabulary."""
    src_metadata = {
        "accelerator_experiments": [
            {"experiment": "ALICE"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CERNFieldsMapper()
    src_record = {"metadata": src_metadata, "created": "2023-01-01"}

    result = mapper.map_value(src_record, ctx, logger)

    assert len(result["cern:experiments"]) == 1
    assert result["cern:experiments"][0]["id"] == "ALICE"
    assert len(ctx.errors) == 0


def test_cern_fields_mapper_experiment_not_found(running_app):
    """Test CERNFieldsMapper with experiment not in vocabulary."""
    src_metadata = {
        "accelerator_experiments": [
            {"experiment": "UNKNOWN_EXP"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CERNFieldsMapper()
    src_record = {"metadata": src_metadata, "created": "2023-01-01"}

    result = mapper.map_value(src_record, ctx, logger)

    assert len(result["cern:experiments"]) == 0
    assert len(ctx.errors) == 0


def test_cern_fields_mapper_mixed_results(running_app):
    """Test CERNFieldsMapper with some found and some not found."""
    src_metadata = {
        "accelerator_experiments": [
            {"accelerator": "LHC", "institution": "CERN", "experiment": "ALICE"},
            {"accelerator": "UNKNOWN", "experiment": "UNKNOWN_EXP"},
        ]
    }
    ctx = MetadataSerializationContext(
        resource_type=ResourceType.OTHER, inspire_id="12345"
    )
    logger = Logger(inspire_id="12345")
    mapper = CERNFieldsMapper()
    src_record = {"metadata": src_metadata, "created": "2023-01-01"}

    result = mapper.map_value(src_record, ctx, logger)

    assert len(result["cern:accelerators"]) == 1
    assert result["cern:accelerators"][0]["id"] == "CERN LHC"

    assert len(result["cern:experiments"]) == 1
    assert result["cern:experiments"][0]["id"] == "ALICE"

    assert len(ctx.errors) == 0
