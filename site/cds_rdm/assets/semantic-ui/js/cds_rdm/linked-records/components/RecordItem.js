// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Item, Label } from "semantic-ui-react";
import _get from "lodash/get";
import { SearchItemCreators } from "@js/invenio_app_rdm/utils";


const layoutProps = (result) => {
  return {
    accessStatusId: _get(result, "ui.access_status.id", "open"),
    accessStatus: _get(result, "ui.access_status.title_l10n", "Open"),
    accessStatusIcon: _get(result, "ui.access_status.icon", "unlock"),
    createdDate: _get(result, "ui.created_date_l10n_long", "Unknown date"),
    creators: _get(result, "ui.creators.creators", []).slice(0, 3),
    resourceType: _get(result, "ui.resource_type.title_l10n", "No resource type"),
    title: _get(result, "metadata.title", "No title"),
    link: _get(result, "links.self_html", "#"),
  };
};

export const RecordListItem = ({ result }) => {
  const {
    accessStatusId,
    accessStatus,
    createdDate,
    creators,
    resourceType,
    title,
    link,
  } = layoutProps(result);

  return (
    <Item>
      <Item.Content>
        {/* Metadata badges */}
        <div className="mb-10">
          <Label size="small">
            {resourceType}
          </Label>

          <Label size="small">
            {createdDate}
          </Label>

          <Label size="small" className={`access-status ${accessStatusId}`}>
            {accessStatus}
          </Label>
        </div>

        {/* Title */}
        <Item.Header className="truncate-lines-2" href={link}>
          {title}
        </Item.Header>

        {/* Creators */}
        <Item.Extra className="truncate-lines-2">
          <SearchItemCreators creators={creators} />
        </Item.Extra>
      </Item.Content>
    </Item>
  );
};

RecordListItem.propTypes = {
  result: PropTypes.object.isRequired,
};
