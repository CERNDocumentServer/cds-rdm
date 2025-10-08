# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Statistics events search index templates.

The templates were overridden to include the custom fields in the search index.

Specifically, the following fields were added to the search index:

- `is_lcds` (boolean): This field marks all statistical events that have been migrated from the legacy CDS system.
- `before_COUNTER` (boolean): This field applies to all migrated events where no information was available to determine whether they were human or robot events. This was later resolved with the implementation of a proper robot-checking mechanism, ensuring COUNTER compliance.

"""
