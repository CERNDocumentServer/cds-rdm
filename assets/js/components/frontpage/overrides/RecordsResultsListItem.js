// This file is part of CDS RDM
// Copyright (C) 2022 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import _get from "lodash/get";
import _truncate from "lodash/truncate";
import _upperCase from "lodash/upperCase";
import React, { Component } from "react";
import PropTypes from "prop-types";
import { Image } from "react-invenio-forms";
import { Container, Item, Label, Icon, Grid } from "semantic-ui-react";

const ResultHeader = ({ result }) => {
  const accessStatusId = _get(result, "ui.access_status.id", "open");
  const accessStatus = _get(result, "ui.access_status.title_l10n", "Open");
  const accessStatusIcon = _get(result, "ui.access_status.icon", "unlock");
  const publicationDate = _get(
    result,
    "ui.publication_date_l10n_long",
    "No publication date found."
  );
  const resourceType = _get(
    result,
    "ui.resource_type.title_l10n",
    "No resource type"
  );
  const title = _get(result, "metadata.title", "No title");
  const version = _get(result, "ui.version", null);
  const community = _get(result, "expanded.parent.communities.default", null);

  // Derivatives
  const uploadLink = `/records/${result.id}`;
  const communityLink = `/communities/${community?.slug}`;
  return (
    <Grid columns="equal" className="m-0">
      <Grid.Column className="title-background">
        <h2 className="rel-m-1">
          <a href={uploadLink}>{_truncate(title, { length: 100 })}</a>
        </h2>
      </Grid.Column>
      <Grid.Column className="metadata-background-color">
        <div className="rel-m-1 text-align-right">
          <h3 className="truncate-lines-3">{_upperCase(resourceType)}</h3>
          {community && (
            <h4 className="truncate-lines-1 rel-mt-1">
              <i>
                <a href={communityLink}>{community?.metadata?.title}</a>
              </i>
            </h4>
          )}
          <Label size="small" className="light-blue-background-color">
            {publicationDate} ({version})
          </Label>
          <Label size="small" className="muted-background-color ml-10">
            {resourceType}
          </Label>
          <Label
            size="small"
            className={`access-status ml-10 ${accessStatusId}`}
          >
            {accessStatusIcon && <Icon name={accessStatusIcon} />}
            {accessStatus}
          </Label>
        </div>
      </Grid.Column>
    </Grid>
  );
};

export class RecordsResultsListItem extends Component {
  render() {
    const { result, key } = this.props;
    const descriptionStripped = _get(result, "ui.description_stripped", null);
    const community = _get(result, "expanded.parent.communities.default", null);
    const truncateLines = community ? 3 : 4;
    return (
      <React.Fragment key={key}>
        <Item className="rel-pt-2 rel-pb-2">
          <Container className="flex">
            <Image
              wrapped
              src={
                community?.links?.logo ||
                "/static/images/square-placeholder.png"
              }
            />

            <Item.Content>
              <Item.Header>
                <ResultHeader result={result} />
              </Item.Header>
              <Item.Description>
                {descriptionStripped && (
                  <p className={`truncate-lines-${truncateLines} rel-m-2`}>
                    {descriptionStripped}
                  </p>
                )}
              </Item.Description>
            </Item.Content>
          </Container>
        </Item>
      </React.Fragment>
    );
  }
}

RecordsResultsListItem.propTypes = {
  result: PropTypes.object.isRequired,
};
