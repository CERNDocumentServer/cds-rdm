// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import React, { useContext } from "react";
import { DatasetContext } from "@js/invenio_requests/data";
import { i18next as requestsI18next } from "@translations/invenio_requests/i18next";
import { Label } from "semantic-ui-react";
import { BasicCERNInformation } from "../../components/deposit/BasicInformation";
import { CDSCarouselItem } from "../../components/communities_carousel/overrides/CarouselItem";
import { CDSRecordsList } from "../../components/frontpage/overrides/RecordsList";
import { CDSRecordsResultsListItem } from "../../components/frontpage/overrides/RecordsResultsListItem";
import {
  CDSRecordsResultsListItemDescription,
  CDSRecordsResultsListItemLabelsAfter,
} from "../../components/search/overrides/CDSRecordsResultsListItemDescription";
import { CDSAffiliationsSuggestions } from "../../components/deposit/overrides/CDSAffiliationsSuggestions";
import { CLCSync } from "../../components/record_details/clc_sync";
import { CommitteeApprovalManageSection } from "../../components/record_details/CommitteeApproval";
import {
  PublishModalComponent,
  SubmitReviewModalComponent,
} from "../../components/deposit/overrides/PublishModal";
import { LockRequestComponent } from "../../components/requests/overrides/LockRequest";
import { TimelineEventBodyComponent } from "../../components/requests/overrides/TimelineEventBody";
import { RecordVersionItemContent } from "../../components/record_details/RecordVersionItem";
import { NewVersionButton } from "../../components/record_details/NewVersionButton";

const RecordManagementContainer = (props) => (
  <>
    <CLCSync {...props} />
    <CommitteeApprovalManageSection {...props} />
  </>
);

const CommitteeApprovalRequestTypeLabel = () => {
  const dataset = useContext(DatasetContext);
  const approvalLabel = dataset?.request?.payload?.approval_label;

  return (
    <Label horizontal className="primary theme-secondary" size="small">
      {approvalLabel || requestsI18next.t("Committee review")}
    </Label>
  );
};

export const overriddenComponents = {
  "InvenioAppRdm.RecordsList.layout": CDSRecordsList,
  "InvenioAppRdm.RecordsResultsListItem.layout": CDSRecordsResultsListItem,
  "InvenioCommunities.CommunitiesCarousel.layout": null,
  "InvenioCommunities.CarouselItem.layout": CDSCarouselItem,
  "InvenioAppRdm.Deposit.BasicInformation.after.container": BasicCERNInformation,
  "InvenioAppRdm.Deposit.CustomFields.container": () => null,
  "ReactInvenioForms.AffiliationsSuggestions.content": CDSAffiliationsSuggestions,
  "InvenioAppRdm.Search.RecordsResultsListItem.labels.after":
    CDSRecordsResultsListItemLabelsAfter,
  "InvenioCommunities.DetailsSearch.RecordsResultsListItem.labels.after":
    CDSRecordsResultsListItemLabelsAfter,
  "InvenioAppRdm.Search.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioCommunities.DetailsSearch.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioAppRdm.RecordLandingPage.RecordManagement.container":
    RecordManagementContainer,
  "InvenioRdmRecords.SubmitReviewModal.container": SubmitReviewModalComponent,
  "InvenioRdmRecords.PublishModal.container": PublishModalComponent,
  "InvenioRdmRecords.RecordLandingPage.RecordManagement.NewVersionButton":
    NewVersionButton,
  "InvenioRequests.LockRequest": LockRequestComponent,
  "RequestTypeLabel.layout.committee-approval": CommitteeApprovalRequestTypeLabel,
  "InvenioAppRdm.RecordVersionsList.Item.container": RecordVersionItemContent,
  "InvenioRequests.TimelineEventBody": TimelineEventBodyComponent,
};
