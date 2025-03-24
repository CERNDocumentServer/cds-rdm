// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2023 CERN.
// Copyright (C) 2020-2022 Northwestern University.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the MIT License; see LICENSE file for more details.

import React, { Component } from "react";

import { FieldLabel } from "react-invenio-forms";
import { Divider, Grid } from "semantic-ui-react";

import PropTypes from "prop-types";
import { AccordionField } from "react-invenio-forms";

export class CERNFields extends Component {
  render() {
    const { key, children, includesPaths, label, active } = this.props;
    const [
      department,
      programme,
      accelerator,
      experiment,
      projects,
      studies,
      facilities,
      beam,
    ] = children;
    return (
      <AccordionField
        key={key}
        includesPaths={includesPaths}
        label={label}
        active={active}
      >
        <Grid padded>
          <Grid.Column computer={16}>{department}</Grid.Column>
          <Grid.Column computer={16}>{programme}</Grid.Column>
        </Grid>
        <FieldLabel htmlFor="CERNFields" icon="bullseye" label="Physics" />
        <Divider fitted />
        <Grid padded>
          <Grid.Column computer={16}>{experiment}</Grid.Column>
          <Grid.Column computer={12}>{accelerator}</Grid.Column>
          <Grid.Column computer={4}>{beam}</Grid.Column>
        </Grid>
        <FieldLabel
          htmlFor="CERNFields"
          icon="chart line"
          label="Research activities"
        />
        <Divider fitted />
        <Grid padded>
          <Grid.Column computer={16}>{projects}</Grid.Column>
          <Grid.Column computer={8}>{studies}</Grid.Column>
          <Grid.Column computer={8}>{facilities}</Grid.Column>
        </Grid>
      </AccordionField>
    );
  }
}

CERNFields.propTypes = {
  includesPaths: PropTypes.array.isRequired,
  label: PropTypes.string,
  children: PropTypes.arrayOf(
    PropTypes.shape({
      field: PropTypes.string.isRequired,
      ui_widget: PropTypes.string.isRequired,
      props: PropTypes.object,
    })
  ).isRequired,
  active: PropTypes.bool,
  key: PropTypes.string,
};

CERNFields.defaultProps = {
  label: "CERN",
  active: true,
  key: "CERNFields",
};
