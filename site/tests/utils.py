# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Task tests."""
from io import BytesIO


def add_file_to_draft(draft_file_service, identity, draft, file_id, content=None):
    """Add file to draft record."""
    if not content:
        content = BytesIO(b"test file content")
    draft_file_service.init_files(identity, draft.id, data=[{"key": file_id}])
    draft_file_service.set_file_content(identity, draft.id, file_id, content)
    draft_file_service.commit_file(identity, draft.id, file_id)
