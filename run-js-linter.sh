#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

# Usage:
#   ./run-js-linter.sh [args]

# Arguments
# -i|--install: installs eslint-config-invenio
set -euo pipefail

INSTALL=0
SCRIPT="lint"

for arg in "$@"; do
	case "$arg" in
		-i|--install) INSTALL=1 ;;
		-f|--fix) SCRIPT="lint:fix" ;;
		*) echo "Unknown argument: $arg" >&2; exit 1 ;;
	esac
done

SITE="$(dirname -- "${BASH_SOURCE[0]}")/site"

if [[ $INSTALL -eq 1 || ! -d "$SITE/node_modules" ]]; then
	pnpm --dir "$SITE" install
fi

pnpm --dir "$SITE" "$SCRIPT"
