// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2025 CERN.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import { AccordionField } from "react-invenio-forms";
import { Grid } from "semantic-ui-react";
import PropTypes from "prop-types";

export class OpenAccessFields extends Component {
  feedbackCfg = {
    "open-access-section": [
      "custom_fields.cern:oa_level",
      "custom_fields.cern:oa_funding_model",
    ],
  };

  render() {
    const { key, children, label, active } = this.props;
    const [oaLevel, oaFundingModel] = children;

    return (
      <AccordionField
        key={key}
        includesPaths={this.feedbackCfg["open-access-section"]}
        label={label}
        active={active}
        id="open-access-section"
      >
        <Grid padded>
          <Grid.Column computer={8}>{oaLevel}</Grid.Column>
          <Grid.Column computer={8}>{oaFundingModel}</Grid.Column>
        </Grid>
      </AccordionField>
    );
  }
}

OpenAccessFields.propTypes = {
  label: PropTypes.string,
  children: PropTypes.array.isRequired,
  active: PropTypes.bool,
  key: PropTypes.string,
};

OpenAccessFields.defaultProps = {
  label: "Open Access",
  active: false,
  key: "OpenAccessFields",
};
