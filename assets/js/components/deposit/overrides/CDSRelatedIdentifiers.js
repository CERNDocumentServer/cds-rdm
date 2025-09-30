import React from "react";
import PropTypes from "prop-types";
import { RelatedWorksField } from "@js/invenio_rdm_records";

export const CDSRelatedIdentifiers = ({ vocabularies }) => {
    return (
      <RelatedWorksField
      fieldPath="metadata.related_identifiers"
      options={vocabularies.metadata.related_identifiers}
      showEmptyValue
    />
  );
};

CDSRelatedIdentifiers.propTypes = {
  vocabularies: PropTypes.object.isRequired,
};