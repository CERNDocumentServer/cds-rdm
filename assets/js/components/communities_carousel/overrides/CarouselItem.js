/*
 * This file is part of Invenio.
 * Copyright (C) 2016-2022 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */

import React from "react";
import PropTypes from "prop-types";
import { Image } from "react-invenio-forms";
import { Card } from "semantic-ui-react";
import { RestrictedLabel } from "@js/invenio_communities/community/labels";

export const CDSCarouselItem = ({ community, defaultLogo, className }) => {
  return (
    <Card className={className}>
      <Image
        src={community.links.logo}
        fallbackSrc={defaultLogo}
        size="small"
        wrapped
        ui={false}
        alt=""
      />
      <Card.Content>
        <Card.Header as="a" href={community.links.self_html}>
          {community.metadata.title}
        </Card.Header>
        {community.metadata.description && (
          <Card.Description
            className="truncate-lines-2"
            content={community.metadata.description}
          />
        )}
      </Card.Content>
      <Card.Content extra>
        <Card.Meta>{community.metadata.ui?.type?.title_l10n}</Card.Meta>
        <Card.Meta className="right floated">
          <RestrictedLabel access={community.access.visibility} />
        </Card.Meta>
      </Card.Content>
    </Card>
  );
};

CDSCarouselItem.propTypes = {
  community: PropTypes.object.isRequired,
  defaultLogo: PropTypes.string.isRequired,
  className: PropTypes.string.isRequired,
};
