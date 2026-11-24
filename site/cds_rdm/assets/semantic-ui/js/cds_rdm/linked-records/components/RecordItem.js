// -*- coding: utf-8 -*-
//
// Copyright (C) 2025 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it under
// the terms of the MIT License; see LICENSE file for more details.

import PropTypes from "prop-types";
import { Card, Image, Item, Label } from "semantic-ui-react";
import _get from "lodash/get";
import { SearchItemCreators } from "@js/invenio_app_rdm/utils";

const THUMBNAIL_PLACEHOLDER = "/static/images/square-placeholder.png";

const layoutProps = (result) => {
  return {
    accessStatusId: _get(result, "ui.access_status.id", "open"),
    accessStatus: _get(result, "ui.access_status.title_l10n", "Open"),
    accessStatusIcon: _get(result, "ui.access_status.icon", "unlock"),
    publicationDate: _get(result, "ui.publication_date_l10n_long", "Unknown date"),
    creators: _get(result, "ui.creators.creators", []).slice(0, 3),
    resourceType: _get(result, "ui.resource_type.title_l10n", "No resource type"),
    title: _get(result, "metadata.title", "No title"),
    link: _get(result, "links.self_html", "#"),
    thumbnail: _get(result, "links.thumbnails.250"),
  };
};

const MetadataLabels = ({
  resourceType,
  publicationDate,
  accessStatusId,
  accessStatus,
}) => (
  <div className="mb-10">
    <Label size="small">{resourceType}</Label>

    <Label size="small">{publicationDate}</Label>

    <Label size="small" className={`access-status ${accessStatusId}`}>
      {accessStatus}
    </Label>
  </div>
);

MetadataLabels.propTypes = {
  resourceType: PropTypes.string.isRequired,
  publicationDate: PropTypes.string.isRequired,
  accessStatusId: PropTypes.string.isRequired,
  accessStatus: PropTypes.string.isRequired,
};

export const RecordGridItem = ({ result }) => {
  const {
    accessStatusId,
    accessStatus,
    publicationDate,
    creators,
    resourceType,
    title,
    link,
    thumbnail,
  } = layoutProps(result);

  return (
    <Card className="linked-record-grid-card">
      <Image
        src={thumbnail || THUMBNAIL_PLACEHOLDER}
        alt=""
        className="linked-record-grid-image"
      />
      <Card.Content>
        <MetadataLabels
          resourceType={resourceType}
          publicationDate={publicationDate}
          accessStatusId={accessStatusId}
          accessStatus={accessStatus}
        />

        <Card.Header as="a" href={link} className="truncate-lines-2">
          {title}
        </Card.Header>

        <Card.Description className="truncate-lines-2">
          <SearchItemCreators creators={creators} />
        </Card.Description>
      </Card.Content>
    </Card>
  );
};

RecordGridItem.propTypes = {
  result: PropTypes.object.isRequired,
};

export const RecordListItem = ({ result }) => {
  const {
    accessStatusId,
    accessStatus,
    publicationDate,
    creators,
    resourceType,
    title,
    link,
    thumbnail,
  } = layoutProps(result);

  return (
    <Item>
      <Item.Image src={thumbnail || THUMBNAIL_PLACEHOLDER} size="tiny" alt="" />
      <Item.Content>
        {/* Metadata badges */}
        <MetadataLabels
          resourceType={resourceType}
          publicationDate={publicationDate}
          accessStatusId={accessStatusId}
          accessStatus={accessStatus}
        />

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
