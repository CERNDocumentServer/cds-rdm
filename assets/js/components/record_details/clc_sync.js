import React, { Component } from "react";
import PropTypes from "prop-types";
import {
  Button,
  Grid,
  Icon,
  Message,
  Checkbox,
  Divider,
  Header,
  Popup,
} from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import { withCancel, http } from "react-invenio-forms";
import { DateTime } from "luxon";

export class CLCSync extends Component {
  constructor(props) {
    super(props);
    this.state = {
      clcSyncRecord: null,
      loading: false,
      error: null,
      autoSync: null,
      showSuccess: false,
    };
  }

  componentDidMount() {
    const recordManagementAppDiv = document.getElementById("recordManagement");
    const clcSyncRecord = JSON.parse(
      recordManagementAppDiv.dataset.clcSyncEntry
    );
    this.setState({
      clcSyncRecord: clcSyncRecord,
      autoSync: clcSyncRecord?.auto_sync,
    });
  }

  componentWillUnmount() {
    if (this.cancellableRequest) {
      this.cancellableRequest.cancel();
    }
  }

  get shouldRenderComponent() {
    const { record } = this.props;
    const recordManagementAppDiv = document.getElementById("recordManagement");

    const allowedResourceTypes = JSON.parse(
      recordManagementAppDiv.dataset.allowedResourceTypes
    );

    const additionalPermissions = JSON.parse(
      recordManagementAppDiv.dataset.additionalPermissions
    );

    const isTypeAllowed = allowedResourceTypes.some((type) =>
      record.metadata.resource_type.id.startsWith(type)
    );
    return isTypeAllowed && additionalPermissions.can_manage_clc_sync;
  }

  syncWithCLC = async (payload, existingId = null) => {
    if (existingId) {
      this.cancellableRequest = withCancel(
        http.put(`/api/clc/${existingId}`, payload, {
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
        })
      );
    } else {
      this.cancellableRequest = withCancel(
        http.post(`/api/clc/`, payload, {
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
        })
      );
    }
    const response = await this.cancellableRequest.promise;
    return response.data;
  };

  setSuccessMessage = () => {
    this.setState({ showSuccess: true });
    setTimeout(() => {
      this.setState({ showSuccess: false });
    }, 5000);
  };

  handleClick = async () => {
    this.setState({ loading: true, error: null });

    const { record } = this.props;
    const { clcSyncRecord, autoSync } = this.state;

    const payload = {
      parent_record_pid: record.parent.id,
      record,
      auto_sync: autoSync,
    };

    try {
      const clcRecordData = await this.syncWithCLC(payload, clcSyncRecord?.id);
      this.setState({
        autoSync: clcRecordData.auto_sync,
        clcSyncRecord: clcRecordData,
      });
      this.setSuccessMessage();
    } catch (error) {
      console.error("Error syncing with CLC:", error);
      this.setState({ error: error });
    } finally {
      this.setState({ loading: false });
    }
  };

  handleToggle = async () => {
    const { record } = this.props;
    const { clcSyncRecord, autoSync } = this.state;
    const newAutoSync = !autoSync;

    const payload = {
      parent_record_pid: record.parent.id,
      record,
      auto_sync: newAutoSync,
    };

    this.setState({ loading: true, error: null, autoSync: newAutoSync });
    try {
      const clcRecordData = await this.syncWithCLC(payload, clcSyncRecord?.id);
      this.setState({
        autoSync: clcRecordData.auto_sync,
        clcSyncRecord: clcRecordData,
      });
      if (newAutoSync) {
        this.setSuccessMessage();
      }
    } catch (error) {
      console.error("Error syncing with CLC:", error);
      this.setState({ error: error });
    } finally {
      this.setState({ loading: false });
    }
  };

  renderErrorMessage = (error) => {
    const errorMessage =
      error?.response?.data?.message ||
      error?.message ||
      i18next.t("An unknown error occurred.");
    return <Message error header={i18next.t("Error")} content={errorMessage} />;
  };

  renderCLCLink = (url) => {
    return url ? (
      <>
        {" "}
        —{" "}
        <a href={url} target="_blank" rel="noopener noreferrer">
          {i18next.t("View CLC record")}
        </a>
      </>
    ) : null;
  };

  render() {
    const { error, loading, autoSync, clcSyncRecord, showSuccess } = this.state;

    if (!this.shouldRenderComponent) {
      return null;
    }

    return (
      <Grid.Column className="pb-20 pt-0">
        <Divider horizontal>
          <Header as="h7">{i18next.t("CERN Library Catalogue Sync")}</Header>
        </Divider>
        <div className="text-align-center">
          <Checkbox
            toggle
            label={autoSync ? i18next.t("Enabled") : i18next.t("Disabled")}
            checked={autoSync}
            disabled={loading}
            onChange={this.handleToggle}
          />
          <Popup
            content={i18next.t(
              "When enabled, this will automatically sync the record with CLC every time it is edited."
            )}
            trigger={
              <span role="button" tabIndex="0">
                <Icon
                  name="question circle outline"
                  className="neutral ml-5 rel-mr-2"
                />
              </span>
            }
          />
          <Button
            color="teal"
            icon
            size="tiny"
            loading={loading}
            disabled={loading || !autoSync}
            onClick={this.handleClick}
            labelPosition="left"
          >
            <Icon name="sync alternate" />
            {i18next.t("Resync")}
          </Button>
        </div>
        {clcSyncRecord && (
          <p className="text-align-center mt-10">
            {clcSyncRecord.status === "SUCCESS" ? (
              <>
                <p>
                  {i18next.t("Last sync")}:{" "}
                  {DateTime.fromISO(clcSyncRecord.last_sync).toFormat(
                    "yyyy-MM-dd HH:mm"
                  )}{" "}
                  (UTC)
                  {this.renderCLCLink(clcSyncRecord.clc_url)}
                </p>
                {showSuccess && (
                  <>
                    <Icon
                      fitted
                      name="check circle"
                      color="green"
                      title={i18next.t("Sync successfully")}
                    />
                    <span className="ml-5 green-color">
                      {i18next.t("Synced successfully!")}
                    </span>
                    <p className="mt-5 text-muted font-size-small font-style-italic">
                      {i18next.t(
                        "Refresh the page if the loan information is not yet displayed."
                      )}
                    </p>
                  </>
                )}
              </>
            ) : clcSyncRecord.status === "FAILED" ? (
              <>
                {i18next.t("Last sync")}: <strong>{i18next.t("FAILED")}</strong>
                {this.renderCLCLink(clcSyncRecord.clc_url)}
                <Popup
                  content={
                    clcSyncRecord.message ||
                    i18next.t("No error message available")
                  }
                  trigger={
                    <Icon
                      className="ml-5"
                      name="exclamation circle"
                      color="red"
                      title={i18next.t("Sync failed")}
                    />
                  }
                />
              </>
            ) : (
              <>
                {i18next.t("Last sync")}: <em>{i18next.t("Pending...")}</em>
                {this.renderCLCLink(clcSyncRecord.clc_url)}
                <Icon
                  className="ml-10"
                  name="clock outline"
                  color="yellow"
                  title={i18next.t("Sync in progress")}
                />
              </>
            )}
          </p>
        )}
        {error && this.renderErrorMessage(error)}
      </Grid.Column>
    );
  }
}

CLCSync.propTypes = {
  record: PropTypes.object.isRequired,
};
