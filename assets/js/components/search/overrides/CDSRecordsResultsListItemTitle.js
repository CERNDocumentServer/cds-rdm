// This file is part of CDS RDM
// Copyright (C) 2026 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import _get from "lodash/get";
import _truncate from "lodash/truncate";
import PropTypes from "prop-types";
import React from "react";
import { Item } from "semantic-ui-react";

export const CDSRecordsResultsListItemTitle = ({
  result,
  titleTruncated,
  viewLink,
}) => {
  const subtitle = _get(result, "ui.additional_titles", []).find(
    (additionalTitle) => additionalTitle.type?.id === "subtitle"
  )?.title;

  return (
    <>
      <Item.Header as="h2" className="theme-primary-text">
        <a href={viewLink}>{titleTruncated}</a>
      </Item.Header>
      {subtitle && (
        <Item.Meta className="record-subtitle truncate-lines-1">
          {_truncate(subtitle, { length: 100 })}
        </Item.Meta>
      )}
    </>
  );
};

CDSRecordsResultsListItemTitle.propTypes = {
  result: PropTypes.object.isRequired,
  titleTruncated: PropTypes.string.isRequired,
  viewLink: PropTypes.string.isRequired,
};
