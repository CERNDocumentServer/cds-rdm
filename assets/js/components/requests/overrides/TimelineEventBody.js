// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import TimelineEventBodyContainer from "@js/invenio_requests/components/TimelineEventBody";
import { parametrize } from "react-overridable";

const parameters = {
  expandedByDefault: true,
};

export const TimelineEventBodyComponent = parametrize(
  TimelineEventBodyContainer,
  parameters
);
