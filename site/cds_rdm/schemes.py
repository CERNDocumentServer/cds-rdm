# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2024 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.
#

"""CDS speficic identifier schemes."""

import re


def cds_reference_number():
    """Define validator for cds reference number."""
    return {
        "validator": lambda value: True,
        "normalizer": lambda value: value,
        "filter": ["cds_ref"],
        "url_generator": None,
    }


aleph_regexp = re.compile(r"\d+CER$", flags=re.I)
inspire_regexp = re.compile(r"\d+$", flags=re.I)
inspire_author_regexp = re.compile(r"INSPIRE-\d+$", flags=re.I)


def is_aleph(val):
    """Test if argument is a PubMed ID.

    Warning: PMID are just integers, with no structure, so this function will
    say any integer is a PubMed ID
    """
    return aleph_regexp.match(val)


def aleph():
    """Define validator for `custom_scheme`."""
    return {
        "validator": is_aleph,
        "normalizer": lambda value: value,
        "filter": ["aleph"],
        "url_generator": None,
    }


def is_inspire(val):
    """Test if argument is an inspire ID

    Warning: INSPIRE IDs are just integers, with no structure, so this function will
    say any integer is an INSPIRE id
    """
    return inspire_regexp.match(val)


def is_inspire_author(val):
    """Test if argument is a PubMed ID.

    Warning: PMID are just integers, with no structure, so this function will
    say any integer is a PubMed ID
    """
    return inspire_author_regexp.match(val)



def inspire():
    """Define validator for inspire."""
    return {
        "validator": is_inspire,
        "normalizer": lambda value: value,
        "filter": ["inspire"],
        "url_generator": None,
    }


def inspire_author():
    """Define validator for inspire author."""
    return {
        "validator": is_inspire_author,
        "normalizer": lambda value: value,
        "filter": ["inspire"],
        "url_generator": None,
    }




def is_cds(val):
    """Test if argument is a valid CERN person ID."""
    pattern = r"^\d+$"
    return bool(re.match(pattern, val))
