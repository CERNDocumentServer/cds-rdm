// This file is part of Invenio-RDM-Records
// Copyright (C) 2020-2025 CERN.
//
// Invenio-RDM-Records is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { Component } from "react";
import { FieldLabel, SelectField } from "react-invenio-forms";
import { Dropdown as SUIDropdown } from "semantic-ui-react";
import PropTypes from "prop-types";

export class DepartmentDropdown extends Component {
  serializeOptions = (options) => {
    if (!options) return [];

    const current = options.filter((o) => o.props?.section === "current");
    const former = options.filter((o) => o.props?.section === "former");
    const other = options.filter((o) => !o.props?.section);

    const result = [];

    if (current.length > 0) {
      result.push({
        key: "header-current",
        text: "",
        content: (
          <SUIDropdown.Header icon="building" content="Current departments" />
        ),
        disabled: true,
        isHeader: true,
      });
      current.forEach((o) =>
        result.push({ key: o.id, value: o.id, text: o.title_l10n })
      );
    }

    if (former.length > 0) {
      result.push({
        key: "header-former",
        text: "",
        content: (
          <SUIDropdown.Header icon="history" content="Former departments" />
        ),
        disabled: true,
        isHeader: true,
      });
      former.forEach((o) =>
        result.push({ key: o.id, value: o.id, text: o.title_l10n })
      );
    }

    other.forEach((o) =>
      result.push({ key: o.id, value: o.id, text: o.title_l10n })
    );

    return result;
  };

  searchFn = (options, query) =>
    options.filter(
      (opt) =>
        !opt.isHeader && opt.text.toLowerCase().includes(query.toLowerCase())
    );

  render() {
    const {
      fieldPath,
      label,
      icon,
      labelIcon: labelIconProp,
      description,
      helpText: helpTextProp,
      placeholder,
      options,
      multiple,
      clearable,
      required,
      disabled,
      optimized,
    } = this.props;

    const helpText = helpTextProp ?? description;
    const labelIcon = labelIconProp ?? icon;

    return (
      <SelectField
        fieldPath={fieldPath}
        label={
          <FieldLabel htmlFor={fieldPath} icon={labelIcon} label={label} />
        }
        options={this.serializeOptions(options)}
        search={this.searchFn}
        aria-label={label}
        multiple={multiple}
        disabled={disabled}
        placeholder={{ role: "option", content: placeholder }}
        clearable={clearable}
        required={required}
        defaultValue={multiple ? [] : ""}
        helpText={helpText}
        optimized={optimized}
      />
    );
  }
}

DepartmentDropdown.propTypes = {
  fieldPath: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  options: PropTypes.array.isRequired,
  icon: PropTypes.string,
  labelIcon: PropTypes.string,
  description: PropTypes.string,
  helpText: PropTypes.string,
  placeholder: PropTypes.string,
  multiple: PropTypes.bool,
  clearable: PropTypes.bool,
  required: PropTypes.bool,
  disabled: PropTypes.bool,
  optimized: PropTypes.bool,
};

DepartmentDropdown.defaultProps = {
  icon: undefined,
  labelIcon: undefined,
  description: undefined,
  helpText: undefined,
  placeholder: undefined,
  multiple: false,
  clearable: true,
  required: false,
  disabled: false,
  optimized: true,
};
