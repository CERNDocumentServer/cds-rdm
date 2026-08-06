// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import _get from "lodash/get";
import PropTypes from "prop-types";
import React from "react";
import { Item, Label } from "semantic-ui-react";

export const CDSRecordsResultsListItemDescription = ({
  result,
  descriptionStripped,
}) => {
  const getMetadataField = (path) => _get(result, path, []);
  const reportNumbers = getMetadataField("metadata.identifiers")
    .filter((id) => id.scheme === "cdsrn")
    .map((id) => id.identifier);
  const cdsReferenceId = getMetadataField("metadata.identifiers").find(
    (id) => id.scheme === "cds_ref"
  )?.identifier;

  const experiments = getMetadataField("custom_fields.cern:experiments").map(
    (exp) => exp.title.en
  );
  const accelerators = getMetadataField("custom_fields.cern:accelerators").map(
    (acc) => acc.title.en
  );

  // CDS reference, accelerators, and/or experiments (row below report numbers).
  const hasSideMeta =
    Boolean(cdsReferenceId) || accelerators.length > 0 || experiments.length > 0;

  return (
    <>
      <Item.Description className="truncate-lines-2">
        {descriptionStripped}
      </Item.Description>

      {reportNumbers.length > 0 && (
        <Item.Meta className="pt-20 truncate-lines-1">
          Report number: {reportNumbers.join(", ")}
        </Item.Meta>
      )}

      {hasSideMeta && (
        <Item.Meta
          className={
            reportNumbers.length > 0
              ? "flex pt-5 search-result-meta-row"
              : "flex pt-20 search-result-meta-row"
          }
        >
          {cdsReferenceId && <span className="mr-5">{cdsReferenceId}</span>}
          {accelerators.length > 0 && (
            <>
              {cdsReferenceId && <span className="ml-5 mr-5">|</span>}
              <div className="truncate-lines-1">
                Accelerators: {accelerators.join(", ")}
              </div>
            </>
          )}
          {experiments.length > 0 && (
            <>
              {(cdsReferenceId || accelerators.length > 0) && (
                <span className="ml-5 mr-5">|</span>
              )}
              <div className="truncate-lines-1">
                Experiments: {experiments.join(", ")}
              </div>
            </>
          )}
        </Item.Meta>
      )}
    </>
  );
};

export const CDSRecordsResultsListItemLabelsAfter = ({ result }) => {
  const epNumber = _get(result, "metadata.identifiers", []).find(
    (id) => id.scheme === "apprn"
  )?.identifier;

  if (!epNumber) {
    return null;
  }

  return (
    <Label horizontal size="small" className="blue" role="note">
      {epNumber}
    </Label>
  );
};

CDSRecordsResultsListItemDescription.propTypes = {
  result: PropTypes.object.isRequired,
  descriptionStripped: PropTypes.string.isRequired,
};

CDSRecordsResultsListItemLabelsAfter.propTypes = {
  result: PropTypes.object.isRequired,
};
