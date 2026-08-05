#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

# Usage:
#   ./run-js-linter.sh [-i|--install] [-f|--fix]

# Arguments
# -i|--install: fetches eslint (v8) and eslint-config-invenio without a full project install
# -f|--fix: auto-fix lint errors

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

FIX=0

for arg in "$@"; do
    case "$arg" in
        -i|--install) ;;
        -f|--fix) FIX=1 ;;
        *) printf "Argument ${RED}$arg${NC} not supported\n" >&2; exit 1 ;;
    esac
done

ROOT="$(dirname -- "${BASH_SOURCE[0]}")"

printf "${GREEN}Run eslint${NC}\n"
if [[ $FIX -eq 1 ]]; then
    pnpm exec eslint --no-error-on-unmatched-pattern --ext .js --fix assets site/cds_rdm/assets
else
    pnpm exec eslint --no-error-on-unmatched-pattern --ext .js assets site/cds_rdm/assets
fi
