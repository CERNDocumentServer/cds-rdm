import React, { Component } from "react";
import PropTypes from "prop-types";
import { CustomFields } from "react-invenio-forms";

export class BasicCERNInformation extends Component {
  render() {
    const { customFieldsUI, record } = this.props;
    return (
      <CustomFields
        config={customFieldsUI}
        record={record}
        templateLoaders={[
          (widget) => import(`@templates/custom_fields/${widget}.js`),
          (widget) =>
            import(`@js/invenio_rdm_records/src/deposit/customFields`),
          (widget) => import(`react-invenio-forms`),
        ]}
        fieldPathPrefix="custom_fields"
      />
    );
  }
}

BasicCERNInformation.propTypes = {
  customFieldsUI: PropTypes.object.isRequired,
  record: PropTypes.object.isRequired,
};
