// This file is part of CDS-RDM
// Copyright (C) 2026 CERN.
//
// CDS-RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React from "react";
import { initDefaultSearchComponents } from "@js/invenio_administration";
import { createSearchAppInit } from "@js/invenio_search_ui";
import { NotificationController } from "@js/invenio_administration";
import { SearchFacets } from "@js/invenio_administration";
import { SearchBar } from "react-searchkit";
import { ErrorMessage, withCancel } from "react-invenio-forms";
import { Modal, Button, Loader, Grid } from "semantic-ui-react";
import { SearchResultItemLayout } from "@js/invenio_app_rdm/administration/auditLogs/search";
import { AuditLogActions } from "@js/invenio_app_rdm/administration/auditLogs/AuditLogActions";
import { ViewRecentChanges } from "@js/invenio_app_rdm/administration/auditLogs/ViewRecentChanges";
import { RecordModerationApi } from "@js/invenio_app_rdm/administration/records/api";
import { RevisionsDiffViewer } from "@js/invenio_app_rdm/administration/components/RevisionsDiffViewer";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { HarvesterSearchBarElement } from "./SearchBar";
import { CustomEmptyResults } from "./EmptyResults";

function formatRevisionError(error) {
  if (!error) {
    return null;
  }
  if (typeof error === "string") {
    return error;
  }
  if (error.response?.status === 403) {
    return i18next.t("You do not have access to view changes for this record.");
  }
  return (
    error.response?.data?.message ||
    error.message ||
    i18next.t("An unexpected error occurred while fetching revisions.")
  );
}

class HarvesterRevisionsDiffViewer extends RevisionsDiffViewer {
  componentDidMount() {
    this.computeDiff();
  }
}

class HarvesterViewRecentChanges extends ViewRecentChanges {
  async fetchPreviousRevision() {
    const { resource } = this.props;
    const {
      resource: record,
      metadata: { revision_id: targetRevision } = { revision_id: null },
    } = resource;
    this.setState({ loading: true });

    try {
      if (!targetRevision) {
        this.setState({
          error: i18next.t("No revision ID found."),
          loading: false,
        });
        return;
      }
      this.cancellableAction = withCancel(
        RecordModerationApi.getLastRevision(record, targetRevision, true)
      );
      const response = await this.cancellableAction.promise;
      const revisions = await response.data;

      this.setState({
        diff: {
          targetRevision: revisions[0],
          srcRevision: revisions.length > 1 ? revisions[1] : {},
        },
        loading: false,
      });
    } catch (error) {
      if (error === "UNMOUNTED") return;
      this.setState({ error: formatRevisionError(error), loading: false });
      console.error(error);
    }
  }

  render() {
    const { error, loading, diff } = this.state;

    if (loading) {
      return (
        <Modal.Content>
          <Loader active inline="centered" size="small" />
        </Modal.Content>
      );
    }

    const errorMessage = formatRevisionError(error);
    if (errorMessage) {
      return (
        <>
          <Modal.Content>
            <ErrorMessage
              header={i18next.t("Unable to fetch revisions.")}
              content={errorMessage}
              icon="exclamation"
              className="text-align-left"
              negative
            />
          </Modal.Content>
          <Modal.Actions>
            <Button onClick={this.handleModalClose}>{i18next.t("Close")}</Button>
          </Modal.Actions>
        </>
      );
    }

    return (
      <>
        <Modal.Content scrolling>
          <HarvesterRevisionsDiffViewer diff={diff} />
        </Modal.Content>
        <Modal.Actions>
          <Grid>
            <Grid.Column floated="left" width={8} textAlign="left">
              <Button
                onClick={this.handleModalClose}
                aria-label={i18next.t("Cancel revision comparison")}
              >
                {i18next.t("Close")}
              </Button>
            </Grid.Column>
          </Grid>
        </Modal.Actions>
      </>
    );
  }
}

class HarvesterAuditLogActions extends AuditLogActions {
  baseOnModalTriggerClick = this.onModalTriggerClick;

  onModalTriggerClick = (e, params) => {
    if (params.dataActionKey !== "view_changes") {
      this.baseOnModalTriggerClick(e, params);
      return;
    }
    const { resource } = this.props;
    this.setState({
      modalOpen: true,
      modalHeader: i18next.t("Recent changes"),
      modalProps: { size: "large" },
      modalBody: (
        <HarvesterViewRecentChanges
          actionCancelCallback={this.closeModal}
          resource={resource}
        />
      ),
    });
  };
}

const domContainer = document.getElementById("invenio-search-config");
if (domContainer) {
  const defaultComponents = initDefaultSearchComponents(domContainer);

  const overriddenComponents = {
    ...defaultComponents,
    "InvenioAdministration.SearchResultItem.layout": SearchResultItemLayout,
    "SearchApp.facets": SearchFacets,
    "InvenioAdministration.ResourceActions": HarvesterAuditLogActions,
    "SearchBar.element": HarvesterSearchBarElement,
    "EmptyResults.element": CustomEmptyResults,
    "SearchApp.searchbarContainer": SearchBar,
  };

  createSearchAppInit(
    overriddenComponents,
    true, // autoInit
    "invenio-search-config",
    false, // searchApiAvailable
    NotificationController
  );
}
