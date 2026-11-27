// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import { useSelector } from "react-redux";
import { Placeholder } from "semantic-ui-react";

export const RelatedRecordsResultsLoader = () => {
  const layout = useSelector((state) => state.query.layout);

  if (layout === "list") {
    return null;
  }

  return (
    <Placeholder fluid>
      <Placeholder.Header image>
        <Placeholder.Line length="long" />
        <Placeholder.Line />
      </Placeholder.Header>
      <Placeholder.Header image>
        <Placeholder.Line length="long" />
        <Placeholder.Line />
      </Placeholder.Header>
    </Placeholder>
  );
};
