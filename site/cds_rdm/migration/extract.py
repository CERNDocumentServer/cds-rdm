# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""CDS-RDM migration extract module."""

from os import listdir
from os.path import isfile, join
from pathlib import Path

import click
import json

from invenio_rdm_migrator.extract import Extract


class LegacyExtract(Extract):
    def __init__(self, dirpath):
        """Constructor."""
        self.dirpath = Path(dirpath).absolute()

    def run(self):

        files = [f for f in listdir(self.dirpath)
                 if isfile(join(self.dirpath, f)) and not f.startswith('.')
                 ]

        for file in files:
            with open(join(self.dirpath, file), 'r') as dump_file:
                data = json.load(dump_file)
                with click.progressbar(data) as records:
                    for dump_record in records:
                        yield dump_record
