// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { useContext } from "react";
import { withState, Sort } from "react-searchkit";
import { Input, Dropdown, Grid, Header, Label, Icon } from "semantic-ui-react";
import { SearchConfigurationContext } from "@js/invenio_search_ui/components";
import { i18next } from "@translations/invenio_administration/i18next";
import { buildTimestampFilter, extractRunIdFromQuery, getStatusColor, getStatusIcon, formatRunOption } from "./utils";
import { DownloadButton } from "./DownloadButton";

/**
 * Custom SearchBar component with run selector
 */
const SearchBarComponent = ({ updateQueryState, currentQueryState }) => {
  const hiddenParams = [
    ["action", "record.publish"],
    ["user_id", "system"],
  ];

  // Get runs from data attributes
  const domContainer = document.getElementById("invenio-search-config");
  const runs = JSON.parse(domContainer?.dataset.harvesterRuns || "[]");
  const defaultRun = JSON.parse(domContainer?.dataset.defaultRun || "null");

  const { sortOptions, sortOrderDisabled } = useContext(SearchConfigurationContext);

  // Derive selected run from the timestamp in the current query — null if user typed a custom range
  const runIdFromQuery = extractRunIdFromQuery(currentQueryState.queryString, runs);
  const selectedRun = runs.find((r) => r.id === runIdFromQuery) || null;

  const [inputValue, setInputValue] = React.useState(currentQueryState.queryString || "");

  // Auto-select default run on mount only if there is no existing query
  React.useEffect(() => {
    if (!currentQueryState.queryString && defaultRun) {
      executeSearch(defaultRun, "");
    }
  }, []);

  const executeSearch = (run, userInput) => {
    const timestampFilter = buildTimestampFilter(run);

    let queryString = timestampFilter;
    if (userInput.trim()) {
      queryString += ` AND (${userInput.trim()})`;
    }

    setInputValue(queryString);
    updateQueryState({
      ...currentQueryState,
      queryString,
      hiddenParams,
    });
  };

  const onRunChange = (e, { value }) => {
    const run = runs.find((r) => r.id === value);
    executeSearch(run, "");
  };

  const onBtnSearchClick = () => {
    updateQueryState({
      ...currentQueryState,
      queryString: inputValue,
      hiddenParams,
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return i18next.t("N/A");
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const calculateDuration = (start, end) => {
    if (!start || !end) return i18next.t("Running...");
    const startDate = new Date(start);
    const endDate = new Date(end);
    const durationMs = endDate - startDate;
    const seconds = Math.floor(durationMs / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const getStatusLabel = (status) => {
    const statusMap = {
      S: i18next.t("SUCCESS"),
      F: i18next.t("FAILURE"),
      R: i18next.t("RUNNING"),
      C: i18next.t("CANCELLED"),
      Q: i18next.t("QUEUED"),
      P: i18next.t("PARTIAL SUCCESS"),
    };
    return statusMap[status?.toUpperCase()] || status?.toUpperCase() || i18next.t("UNKNOWN");
  };

  const runOptions = runs.map(formatRunOption);

  return (
    <Grid>
      <Grid.Row>
        <Grid.Column width={16}>
          <Header as="h4">{i18next.t("Select Harvest Run")}</Header>
          <Dropdown
            fluid
            selection
            placeholder={i18next.t("Select a harvest run...")}
            options={runOptions}
            value={selectedRun?.id || ""}
            onChange={onRunChange}
          />

          {selectedRun && (
            <div className="harvester-run-details">
              <div className="details-row">
                {/* Status */}
                <div>
                  <Label color={getStatusColor(selectedRun.status)} size="small">
                    <Icon name={getStatusIcon(selectedRun.status)} />
                    {getStatusLabel(selectedRun.status)}
                  </Label>
                </div>

                {/* Duration */}
                <div className="detail-item">
                  <Icon name="clock outline" color="grey" size="small" />
                  <span>{calculateDuration(selectedRun.started_at, selectedRun.finished_at)}</span>
                </div>

                {/* Started */}
                <div className="detail-item">
                  <Icon name="play circle" color="grey" size="small" />
                  <span>{formatDate(selectedRun.started_at)}</span>
                </div>

                {/* Finished */}
                {selectedRun.finished_at && (
                  <div className="detail-item">
                    <Icon name="stop circle" color="grey" size="small" />
                    <span>{formatDate(selectedRun.finished_at)}</span>
                  </div>
                )}
              </div>

              {/* Message on separate line if exists */}
              {selectedRun.message && (
                <div className="run-message">
                  <Icon name="info circle" color="grey" size="small" />
                  <span>{selectedRun.message}</span>
                </div>
              )}
            </div>
          )}
        </Grid.Column>
      </Grid.Row>
      <Grid.Row>
        <Grid.Column width={11}>
          <Header as="h4">{i18next.t("Search Logs")}</Header>
          <Input
            action={{
              icon: "search",
              onClick: onBtnSearchClick,
              color: "primary",
            }}
            fluid
            placeholder={i18next.t("Search or enter custom @timestamp:[\"from\" TO \"to\"] range...")}
            onChange={(_, { value }) => {
              setInputValue(value);
            }}
            value={inputValue}
            onKeyPress={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                onBtnSearchClick();
              }
            }}
          />
        </Grid.Column>
        <Grid.Column width={3} verticalAlign="bottom">
          <Sort
            sortOrderDisabled={sortOrderDisabled}
            values={sortOptions}
            ariaLabel={i18next.t("Sort")}
          />
        </Grid.Column>
        <Grid.Column width={2} verticalAlign="bottom">
          <DownloadButton />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  );
};

export const HarvesterSearchBarElement = withState(SearchBarComponent);
