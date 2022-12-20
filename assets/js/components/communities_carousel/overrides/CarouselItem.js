/*
 * This file is part of Invenio.
 * Copyright (C) 2016-2022 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import PropTypes from "prop-types";
import _truncate from "lodash/truncate";
import { Image } from "react-invenio-forms";
import { Grid, Header, Item } from "semantic-ui-react";

export const CDSCarouselItem = ({ community, defaultLogo, className }) => {
  return (
    <Item className={`carousel ${className}`} image key={community.id}>
      <Image
        src={community.links.logo}
        fallbackSrc={defaultLogo}
        size="medium"
      />
      <Grid>
        <Grid.Column computer={12} mobile={16} tablet={10} largeScreen={13} widescreen={13} floated="right">
          <Item.Content className="rel-pt-2 rel-pb-2">
            <Item.Header stackable>
              <Header as="a" size="medium" href={community.links.self_html}>
                {community.metadata.title}
              </Header>
            </Item.Header>
            {community.metadata.description && (
              <Item.Description
                className="truncate-lines-6"
                content={community.metadata.description}
              />
            )}
          </Item.Content>
        </Grid.Column>
      </Grid>
    </Item>
  );
};

CDSCarouselItem.propTypes = {
  community: PropTypes.object.isRequired,
  defaultLogo: PropTypes.string.isRequired,
  className: PropTypes.string.isRequired,
};
