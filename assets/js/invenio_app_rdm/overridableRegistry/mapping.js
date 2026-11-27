// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { CREATIBUTORS_FILE_MODAL_ID } from "@js/invenio_rdm_records";
import { BasicCERNInformation } from "../../components/deposit/BasicInformation";
import { CDSCarouselItem } from "../../components/communities_carousel/overrides/CarouselItem";
import { CDSRecordsList } from "../../components/frontpage/overrides/RecordsList";
import { CDSRecordsResultsListItem } from "../../components/frontpage/overrides/RecordsResultsListItem";
import {
  CDSRecordsResultsListItemDescription,
  CDSRecordsResultsListItemLabelsAfter,
} from "../../components/search/overrides/CDSRecordsResultsListItemDescription";
import { CDSRecordsResultsListItemTitle } from "../../components/search/overrides/CDSRecordsResultsListItemTitle";
import { CDSAffiliationsSuggestions } from "../../components/deposit/overrides/CDSAffiliationsSuggestions";
import {
  PublishModalComponent,
  SubmitReviewModalComponent,
} from "../../components/deposit/overrides/PublishModal";
import { LockRequestComponent } from "../../components/requests/overrides/LockRequest";
import { TimelineEventBodyComponent } from "../../components/requests/overrides/TimelineEventBody";
import { RecordVersionItemContent } from "../../components/record_details/RecordVersionItem";
import { NewVersionButton } from "../../components/record_details/NewVersionButton";
import { CreatibutorsFileModalComponent } from "../../components/deposit/overrides/CreatibutorsFileModal";
import { RecordManagementContainer } from "../../components/record_details/overrides/RecordManagementContainer";
import { CommitteeApprovalRequestTypeLabel } from "../../components/requests/overrides/CommitteeApprovalRequestTypeLabel";

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
  "InvenioAppRdm.Search.RecordsResultsListItem.title": CDSRecordsResultsListItemTitle,
  "InvenioCommunities.DetailsSearch.RecordsResultsListItem.title":
    CDSRecordsResultsListItemTitle,
  "InvenioAppRdm.Search.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioCommunities.DetailsSearch.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioAppRdm.RecordLandingPage.RecordManagement.container":
    RecordManagementContainer,
  [CREATIBUTORS_FILE_MODAL_ID]: CreatibutorsFileModalComponent,
  "InvenioRdmRecords.SubmitReviewModal.container": SubmitReviewModalComponent,
  "InvenioRdmRecords.PublishModal.container": PublishModalComponent,
  "InvenioRdmRecords.RecordLandingPage.RecordManagement.NewVersionButton":
    NewVersionButton,
  "InvenioRequests.LockRequest": LockRequestComponent,
  "InvenioAppRdm.RecordVersionsList.Item.container": RecordVersionItemContent,
  "InvenioRequests.TimelineEventBody": TimelineEventBodyComponent,
  "RequestTypeLabel.layout.committee-approval": CommitteeApprovalRequestTypeLabel,
};
