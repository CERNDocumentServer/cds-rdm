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


aleph_regexp = re.compile(r"\d+(CER|MMD){0,2}$", flags=re.I)
inspire_regexp = re.compile(
    r"(?:\d+$|[A-Z]\d{2}-\d{2}-\d{2}\.\d+)", flags=re.I
)  # Matches a string ending with digits (e.g. "1234") or an Inspire conference ID (e.g. "C18-07-09.6")
inspire_author_regexp = re.compile(r"INSPIRE-\d+$", flags=re.I)
handle_regexp = re.compile(r"\d+(?:\.\d+)*/[^\s]+", flags=re.I)
cds_rdm_regexp = re.compile(r"[a-z0-9]{5}-[a-z0-9]{5}", flags=re.I)
legacy_cds_pattern = re.compile(r"^\d+$", flags=re.I)
is_indico_regexp = re.compile(r"^[a-zA-Z0-9]+$", flags=re.I)


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


def is_indico(val):
    """Test if argument is an Indico ID.

    Warning: Indico IDs are just integers, with no structure, so this function will
    say any integer is an Indico id
    """
    return str(val).isdigit()


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


def is_cds(val):
    """Test if argument is a valid cds-rdm or legacy id."""
    return legacy_cds_pattern.match(val) or cds_rdm_regexp.match(val)


def generate_cds_url(scheme, value):
    """Generate a URL for a given normalized CDS id."""
    if cds_rdm_regexp.match(value):
        return f"https://repository.cern/records/{value}"
    elif legacy_cds_pattern.match(value):
        return f"https://cds.cern.ch/record/{value}"
    return ""


def cds():
    """Define scheme for CDS."""
    return {
        "validator": is_cds,
        "normalizer": lambda value: value,
        "url_generator": generate_cds_url,
    }


def is_indico(val):
    """Test if argument is a valid Indico id."""
    return is_indico_regexp.match(val)


def indico():
    """Define scheme for Indico Links."""
    return {
        "validator": is_indico,
        "normalizer": lambda value: value,
        "url_generator": lambda scheme, value: f"https://indico.cern.ch/event/{value}",
    }


def is_handle(val):
    """Test if argument is a valid handle."""
    return handle_regexp.match(val)
