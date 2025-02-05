// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import _get from "lodash/get";
import PropTypes from "prop-types";
import React from "react";
import { Item } from "semantic-ui-react";

export const CDSRecordsResultsListItemDescription = ({
  result,
  descriptionStripped,
}) => {
  const getMetadataField = (path) => _get(result, path, []);

  const cdsReferenceId = getMetadataField("metadata.identifiers").find(
    (id) => id.scheme === "cds_ref"
  )?.identifier;

  const experiments = getMetadataField("custom_fields.cern:experiments").map(
    (exp) => exp.title.en
  );
  const accelerators = getMetadataField("custom_fields.cern:accelerators").map(
    (acc) => acc.title.en
  );

  const hasMetaData =
    cdsReferenceId || accelerators.length > 0 || experiments.length > 0;
  const referenceOrAccelerators = cdsReferenceId || accelerators.length > 0;
  return (
    <>
      <Item.Description className="truncate-lines-2">
        {descriptionStripped}
      </Item.Description>

      {hasMetaData && (
        <Item.Meta className="pt-20">
          {cdsReferenceId && <span className="mr-5">{cdsReferenceId}</span>}
          {accelerators.length > 0 && (
            <>
              {cdsReferenceId && <span className="ml- mr-5">|</span>}
              <span className={cdsReferenceId ? "ml-5 mr-5" : "mr-5"}>
                Accelerators: {accelerators.join(", ")}
              </span>
            </>
          )}
          {experiments.length > 0 && (
            <>
              {referenceOrAccelerators && <span className="ml-5 mr-5">|</span>}
              <span className={referenceOrAccelerators ? "ml-5 mr-5" : "mr-5"}>
                Experiments: {experiments.join(", ")}
              </span>
            </>
          )}
        </Item.Meta>
      )}
    </>
  );
};

CDSRecordsResultsListItemDescription.propTypes = {
  result: PropTypes.object.isRequired,
  descriptionStripped: PropTypes.string.isRequired,
};
