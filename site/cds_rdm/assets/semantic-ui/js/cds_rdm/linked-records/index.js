// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import { createRoot } from "react-dom/client";
import { LinkedRecordsSearch } from "./LinkedRecordsSearch";

const linkedRecordsContainer = document.getElementById("cds-linked-records");

if (linkedRecordsContainer) {
  const endpoint = linkedRecordsContainer.dataset.apiEndpoint;
  const searchQuery = linkedRecordsContainer.dataset.searchQuery;

  const root = createRoot(linkedRecordsContainer);
  root.render(<LinkedRecordsSearch endpoint={endpoint} searchQuery={searchQuery} />);
}
