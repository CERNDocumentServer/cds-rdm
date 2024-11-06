// This file is part of CDS RDM
// Copyright (C) 2024 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React from "react";
import PropTypes from "prop-types";
import { Header, Image, Label } from "semantic-ui-react";

export const CDSCreatibutorsRemoteSelectItem = ({
  creatibutor,
  isOrganization,
  idString,
  affNames,
}) => {
  const makeIdEntry = (identifier) => {
    let icon = null;
    let link = null;
    const { department, group, section } = creatibutor.props || {};
    const workgroup = [department, group, section].filter(Boolean).join('-');

    if (identifier.scheme === "orcid") {
      icon = "/static/images/orcid.svg";
      link = "https://orcid.org/" + identifier.identifier;
    } else if (identifier.scheme === "gnd") {
      icon = "/static/images/gnd-icon.svg";
      link = "https://d-nb.info/gnd/" + identifier.identifier;
    } else if (identifier.scheme === "ror") {
      icon = "/static/images/ror-icon.svg";
      link = "https://ror.org/" + identifier.identifier;
    } else if (identifier.scheme === "isni" || identifier.scheme === "grid") {
      return null;
    } else if (identifier.scheme === "cds") {
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
    }
    else {
      return (
        <>
          {identifier.scheme}: {identifier.identifier}
        </>
      );
    }

    return (
      <span key={identifier.identifier} className="font-weight-normal">
        {link ? (
          <a href={link} target="_blank" rel="noopener noreferrer">
            <Image
              src={icon}
              className="inline-id-icon ml-5 mr-5"
              verticalAlign="middle"
            />
            {identifier.scheme === "orcid" ? identifier.identifier : null}
          </a>
        ) : (
          <span>
            <Image
              src={icon}
              className="inline-id-icon ml-5 mr-5"
              verticalAlign="middle"
            />
            {identifier.scheme === "orcid" ? identifier.identifier : null}
          </span>
        )
        }
      </span>
    );
  };

  const CDSidString = [];
  creatibutor.identifiers?.forEach((i) => {
    CDSidString.push(makeIdEntry(i));
  });

  const isUnlisted = creatibutor.tags?.includes("unlisted");
  return (
    <Header color={`${isUnlisted ? "grey" : ""}`} >
      {creatibutor.name} {CDSidString.length ? <>{CDSidString}</> : null}
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