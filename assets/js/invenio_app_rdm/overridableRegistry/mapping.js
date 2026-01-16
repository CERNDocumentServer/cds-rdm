// This file is part of CDS RDM
// Copyright (C) 2025 CERN.
//
// CDS RDM is free software; you can redistribute it and/or modify it
// under the terms of the GPL-2.0 License; see LICENSE file for more details.

import { BasicCERNInformation } from "../../components/deposit/BasicInformation";
import { CDSCarouselItem } from "../../components/communities_carousel/overrides/CarouselItem";
import { CDSRecordsList } from "../../components/frontpage/overrides/RecordsList";
import { CDSRecordsResultsListItem } from "../../components/frontpage/overrides/RecordsResultsListItem";
import { CDSRecordsResultsListItemDescription } from "../../components/search/overrides/CDSRecordsResultsListItemDescription";
import { CDSAffiliationsSuggestions } from "../../components/deposit/overrides/CDSAffiliationsSuggestions";
import { CLCSync } from "../../components/record_details/clc_sync";
import {
  PublishModalComponent,
  SubmitReviewModalComponent,
} from "../../components/deposit/overrides/PublishModal";
import { LockRequestComponent } from "../../components/requests/overrides/LockRequest";
import { RecordVersionItemContent } from "../../components/record_details/RecordVersionItem";

export const overriddenComponents = {
  "InvenioAppRdm.RecordsList.layout": CDSRecordsList,
  "InvenioAppRdm.RecordsResultsListItem.layout": CDSRecordsResultsListItem,
  "InvenioCommunities.CommunitiesCarousel.layout": null,
  "InvenioCommunities.CarouselItem.layout": CDSCarouselItem,
  "InvenioAppRdm.Deposit.BasicInformation.after.container":
    BasicCERNInformation,
  "InvenioAppRdm.Deposit.CustomFields.container": () => null,
  "ReactInvenioForms.AffiliationsSuggestions.content":
    CDSAffiliationsSuggestions,
  "InvenioAppRdm.Search.RecordsResultsListItem.description":
    CDSRecordsResultsListItemDescription,
  "InvenioAppRdm.RecordLandingPage.RecordManagement.container": CLCSync,
  "InvenioRdmRecords.SubmitReviewModal.container": SubmitReviewModalComponent,
  "InvenioRdmRecords.PublishModal.container": PublishModalComponent,
  "InvenioRequests.LockRequest": LockRequestComponent,
  "InvenioAppRdm.RecordVersionsList.Item.container": RecordVersionItemContent,
};
