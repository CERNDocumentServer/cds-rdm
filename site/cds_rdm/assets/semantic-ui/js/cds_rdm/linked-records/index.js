// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import ReactDOM from "react-dom";
import { LinkedRecordsSearch } from "./LinkedRecordsSearch";

const linkedRecordsContainer = document.getElementById("cds-linked-records");
console.log(linkedRecordsContainer);

if (linkedRecordsContainer) {
  const endpoint = linkedRecordsContainer.dataset.apiEndpoint;
  const searchQuery = linkedRecordsContainer.dataset.searchQuery;

  ReactDOM.render(
    <LinkedRecordsSearch endpoint={endpoint} searchQuery={searchQuery} />,
    linkedRecordsContainer
  );
}
