// This file is part of CDS RDM
// Copyright (C) 2024 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Header, Image } from "semantic-ui-react";

export const CDSCreatibutorsRemoteSelectItem = ({
  creatibutor,
  isOrganization,
  idString,
  affNames,
}) => {
  if (creatibutor.props?.is_cern) {
    const cmp = (
      <span className="font-weight-normal" key={creatibutor.props.email}>
        <Image
          src="/static/images/cern-favicon.ico"
          className="inline-id-icon ml-5 mr-5"
          verticalAlign="middle"
        />
        {creatibutor.props.email} 22
      </span>
    );
    if (!idString.some(item => item.key === cmp.key)) {
      idString.push(cmp);
    }
  }

  const isUnlisted = creatibutor.tags?.includes("unlisted");

  return (
    <Header
      className={`${isUnlisted ? "color-grey" : ""}`}
    >
      {creatibutor.name} {idString.length ? <>({idString})</> : null}
      <Header.Subheader>
        {isOrganization ? creatibutor.acronym : affNames}
      </Header.Subheader>
    </Header>
  );
};

CDSCreatibutorsRemoteSelectItem.propTypes = {
  creatibutor: PropTypes.object.isRequired,
  isOrganization: PropTypes.bool.isRequired,
  idString: PropTypes.array,
  affNames: PropTypes.string,
};

CDSCreatibutorsRemoteSelectItem.defaultProps = {
  idString: [],
  affNames: "",
};