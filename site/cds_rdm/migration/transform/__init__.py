# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM base migration model module."""

from cds_dojson.overdo import OverdoBase

# Matching to a correct model is happening here
migrator_marc21 = OverdoBase(entry_point_models="cds_rdm.migrator.models")
