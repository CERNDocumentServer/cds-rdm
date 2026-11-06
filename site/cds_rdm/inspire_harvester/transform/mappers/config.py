# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE to CDS harvester configuration."""

# INSPIRE ``material`` values that mark a DOI/document as a correction of
# the main publication. Their DOIs are mapped to related identifiers
# (``issupplementedby``) and their files are tagged with the material.
INSPIRE_CORRECTION_MATERIALS = {
    "erratum": {"resource_type": "publication-other"},
    "corrigendum": {"resource_type": "publication-other"},
    "addendum": {"resource_type": "publication-other"},
}
