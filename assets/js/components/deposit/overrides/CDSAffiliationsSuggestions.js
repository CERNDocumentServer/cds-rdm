// This file is part of CDS RDM
// Copyright (C) 2024 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Header, Image, Label } from "semantic-ui-react";

export const CDSAffiliationsSuggestions = ({
  creatibutor,
  isOrganization,
  idString,
  makeSubheader,
  makeIdEntry,
}) => {
  const CDSmakeIdEntry = (creatibutor) => {
    const { props } = creatibutor;
    const { email, department, group, section } = props || {};
    const workgroup = [department, group, section].filter(Boolean).join("-");
    return (
      <span className="font-weight-normal" key={email}>
        <Image
          src="/static/images/cern-favicon.ico"
          className="inline-id-icon ml-5 mr-5"
          verticalAlign="middle"
        />
        {email}
        {workgroup && <Label size="tiny">{workgroup}</Label>}
      </span>
    );
  };

  const CDSidString = [];
  creatibutor.identifiers?.forEach((i) => {
    CDSidString.push(makeIdEntry(i));
  });

  // CERN specific
  if (creatibutor.props?.is_cern) {
    CDSidString.push(CDSmakeIdEntry(creatibutor));
  }

  let name = creatibutor.name;
  const subheader = makeSubheader(creatibutor, isOrganization);

  const isUnlisted = creatibutor.tags?.includes("unlisted");

  return (
    <Header color={isUnlisted ? "grey" : ""}>
      {name} {CDSidString.length > 0 && CDSidString}
      {subheader.length > 0 && <Header.Subheader>{subheader}</Header.Subheader>}
    </Header>
  );
};

CDSAffiliationsSuggestions.propTypes = {
  creatibutor: PropTypes.object.isRequired,
  isOrganization: PropTypes.bool.isRequired,
  makeIdEntry: PropTypes.func.isRequired,
  makeSubheader: PropTypes.func.isRequired,
  idString: PropTypes.array,
};

CDSAffiliationsSuggestions.defaultProps = {
  idString: [],
};
