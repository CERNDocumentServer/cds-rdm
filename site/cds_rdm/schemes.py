# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""CDS specific identifier schemes."""

import re


def cds_reference_number():
    """Define validator for cds reference number."""
    return {"validator": lambda value: True, "normalizer": lambda value: value}


aleph_regexp = re.compile(r"\d+(CER){0,2}$", flags=re.I)
inspire_regexp = re.compile(r"\d+$", flags=re.I)
inspire_author_regexp = re.compile(r"INSPIRE-\d+$", flags=re.I)
handle_regexp = re.compile(r"\d+(?:\.\d+)*/[^\s]+", flags=re.I)
cds_rdm_regexp = re.compile(r"[a-z0-9]{5}-[a-z0-9]{5}", flags=re.I)


def is_aleph(val):
    """Test if argument is a PubMed ID.

    Warning: PMID are just integers, with no structure, so this function will
    say any integer is a PubMed ID
    """
    return aleph_regexp.match(val)


def normalize_aleph(val):
    """Normalize aleph."""
    m = aleph_regexp.match(val)
    return m.group(1)


def aleph():
    """Define validator for `custom_scheme`."""
    return {
        "validator": is_aleph,
        "normalizer": lambda value: value,
    }


def is_inspire(val):
    """Test if argument is an Inspire ID.

    Warning: INSPIRE IDs are just integers, with no structure, so this function will
    say any integer is an INSPIRE id
    """
    return inspire_regexp.match(val)


def is_inspire_author(val):
    """Test if argument is an inspire author ID."""
    return inspire_author_regexp.match(val)


def inspire():
    """Define validator for Inspire."""
    return {
        "validator": is_inspire,
        "normalizer": lambda value: value,
    }


def inspire_author():
    """Define validator for Inspire author."""
    return {
        "validator": is_inspire_author,
        "normalizer": lambda value: value,
    }


def is_legacy_cds(val):
    """Test if argument is a valid legacy id."""
    pattern = r"^\d+$"
    return bool(re.match(pattern, val))


def legacy_cds():
    """Define scheme for CDS."""
    return {
        "validator": is_legacy_cds,
        "normalizer": lambda value: value,
        "url_generator": lambda scheme, value: f"https://cds.cern.ch/record/{value}",
    }


def is_handle(val):
    """Test if argument is a valid handle."""
    return handle_regexp.match(val)


def is_cds_rdm(val):
    """Test if argument is a valid CDS RDM id."""
    return cds_rdm_regexp.match(val)
