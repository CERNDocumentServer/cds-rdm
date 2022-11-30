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
    <Item
      className={`carousel flex align-items-center ${className}`}
      key={community.id}
    >
      <Image src={community.links.logo} fallbackSrc={defaultLogo} />
      <Item.Content className="rel-m-1">
        <Item.Header as={Grid} stackable className="rel-pb-1 rel-mt-1 rel-mr-5">
          <Header as="a" size="medium" href={community.links.self_html}>
            {community.metadata.title}
          </Header>
        </Item.Header>
        {community.metadata.description && (
          <Item.Description
            className="truncate-lines-6 rel-m-2"
            content={community.metadata.description}
          />
        )}
      </Item.Content>
    </Item>
  );
};

CDSCarouselItem.propTypes = {
  community: PropTypes.object.isRequired,
  defaultLogo: PropTypes.string.isRequired,
  className: PropTypes.string.isRequired,
};
