// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import { Container } from "semantic-ui-react";

export const NoResults = () => {
  return (
    <Container align="left">
      <p>
        <em>No related content for this record</em>
      </p>
    </Container>
  );
};
