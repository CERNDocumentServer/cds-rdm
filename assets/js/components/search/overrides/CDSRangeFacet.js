// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { RangeFacet } from "react-searchkit";
import { parametrize } from "react-overridable";

export const parameters = {
  defaultRanges: [
    { label: "Last 1 year", type: "years", value: 1 },
    { label: "Last 5 years", type: "years", value: 5 },
    { label: "Last 6 months", type: "months", value: 6 },
  ],
  enableCustomRange: true,
};

export const CDSRangeFacet = parametrize(RangeFacet, parameters);
