// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { Segment, Header, Icon } from "semantic-ui-react";
import { i18next } from "@translations/invenio_administration/i18next";

/**
 * Custom Empty Results component (without showing the query)
 */
export const CustomEmptyResults = () => {
  return (
    <Segment placeholder textAlign="center" className="harvester-empty-results">
      <Header icon>
        <Icon name="search" />
        {i18next.t("No logs found")}
      </Header>
      <Segment.Inline>
        <p>{i18next.t("No logs match your current filters. Try selecting a different run or adjusting your search.")}</p>
      </Segment.Inline>
    </Segment>
  );
};
