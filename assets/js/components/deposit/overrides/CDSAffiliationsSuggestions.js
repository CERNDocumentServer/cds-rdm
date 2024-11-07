// This file is part of CDS RDM
// Copyright (C) 2024 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Header, Image, Label } from "semantic-ui-react";

export const CDSAffiliationsSuggestions = ({
  creatibutor,
  isOrganization,
  idString,
  makeSubheader,
  makeIdEntry
}) => {
  const CDSmakeIdEntry = (identifier) => {
    let icon, link;

    switch (identifier.scheme) {
      case "orcid":
        icon = "/static/images/orcid.svg";
        link = `https://orcid.org/${identifier.identifier}`;
        break;
      case "gnd":
        icon = "/static/images/gnd-icon.svg";
        link = `https://d-nb.info/gnd/${identifier.identifier}`;
        break;
      case "ror": // ROR doesn't recommend displaying ROR IDs
      case "isni":
      case "grid":
        return; // Skip these schemes
      case "cds":
        const { department, group, section } = creatibutor.props || {};
        const workgroup = [department, group, section].filter(Boolean).join('-');
        icon = "/static/images/cern-favicon.ico";
        return (
          <span className="font-weight-normal" key={creatibutor.props.email}>
            <Image
              src="/static/images/cern-favicon.ico"
              className="inline-id-icon ml-5 mr-5"
              verticalAlign="middle"
            />
            {creatibutor.props.email}
            {workgroup &&
              <Label size="tiny" >
                {workgroup}
              </Label>}
          </span>
        )
      default:
        return (
          <>
            {identifier.scheme}: {identifier.identifier}
          </>
        );
    }

    return (
      <span key={identifier.identifier}>
        <a href={link} target="_blank" rel="noopener noreferrer">
          <Image src={icon} className="inline-id-icon mr-5" verticalAlign="middle" />
          {identifier.scheme === "orcid" && identifier.identifier}
        </a>
      </span>
    );
  };

  const CDSidString = [];
  creatibutor.identifiers?.forEach((i) => {
    CDSidString.push(CDSmakeIdEntry(i));
  });

  let name = creatibutor.name;
  const subheader = makeSubheader(creatibutor, isOrganization);

  return (
    <Header>
      {name} {CDSidString.length > 0 && <>{CDSidString}</>}
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