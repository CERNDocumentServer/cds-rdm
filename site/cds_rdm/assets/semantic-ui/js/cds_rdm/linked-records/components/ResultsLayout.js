// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Grid, Item } from "semantic-ui-react";

export const ResultsListLayout = ({ results }) => (
  <Item.Group unstackable divided relaxed link>
    {results}
  </Item.Group>
);

ResultsListLayout.propTypes = {
  results: PropTypes.array.isRequired,
};
