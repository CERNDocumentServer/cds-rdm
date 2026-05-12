import React, { useMemo } from "react";
import { Icon, List } from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import PropTypes from "prop-types";
import { CopyButton } from "@js/invenio_app_rdm/components/CopyButton";

function readEpApprovalData() {
  const el = document.getElementById("recordManagement");
  if (!el) return null;
  try {
    return JSON.parse(el.dataset.epApproval || "null");
  } catch (_) {
    return null;
  }
}

export const RecordVersionItemContent = ({ item, activeVersion, doi }) => {
  const epApproval = useMemo(readEpApprovalData, []);

  // --- Internal draft side ---
  // versions_cf is a map of recid → CF fields for every CF-carrying version.
  // Each item looks up its own recid so badges are correct regardless of which
  // version is currently being viewed.
  const cf = epApproval?.versions_cf?.[item.id] || {};
  const approvedReportNumber = cf.reportnumber;
  const approvedVersion = cf.version;   // recid of the originally approved version
  const publicRecordId = cf.public_record_id;  // only set on the source version

  const isApprovedVersion = !!approvedReportNumber && approvedVersion === item.id;
  // public_record_id is written only to the source version, so its presence means
  // this item IS the source.
  const isPublicSourceVersion = !!publicRecordId;
  // If approved and source are the same version, show only the public record link.
  const sameVersion = isApprovedVersion && isPublicSourceVersion;

  // --- Public record side ---
  // is_public_approved_record is set when viewing the public copy.
  // draft_record_id links back to the internal draft it was created from.
  const isPublicRecord = epApproval?.is_public_approved_record;
  const draftRecordId = epApproval?.draft_record_id;

  return (
    <List.Item key={item.id} {...(activeVersion && { className: "version active" })}>
      <List.Content floated="left">
        {activeVersion ? (
          <span className="text-break">
            {i18next.t("Version {{- version}}", { version: item.version })}
          </span>
        ) : (
          <a href={`/records/${item.id}`} className="text-break">
            {i18next.t("Version {{- version}}", { version: item.version })}
          </a>
        )}

        {/* Approved version: show report number. If this is also the source for
            the public record (same version), replace with the public record link.
            If public record was created from a different version, show label only. */}
        {isApprovedVersion && !sameVersion && (
          <>
            {" "}
            <span className="text-muted-darken">
              <Icon name="check circle" size="small" />
              {approvedReportNumber}
            </span>
          </>
        )}

        {/* Public source version: link to public record with report number. */}
        {isPublicSourceVersion && (
          <>
            {" "}
            <a
              href={`/records/${publicRecordId}`}
              target="_blank"
              rel="noreferrer"
              className="text-muted-darken"
            >
              <Icon name="external alternate" size="small" />
              {approvedReportNumber}
            </a>
          </>
        )}

        {/* Public record: show "See collaboration reviewed version" link next to
            the version, pointing back to the internal draft. */}
        {isPublicRecord && item.version === "v1" && draftRecordId && (
          <>
            {" "}
            <a href={`/records/${draftRecordId}`} className="text-muted-darken">
              <Icon name="external alternate" size="small" />
              {i18next.t("Reviewed version")}
            </a>
          </>
        )}

        {doi && (
          <a
            href={`https://doi.org/${doi}`}
            className={"doi" + (activeVersion ? " text-muted-darken" : " text-muted")}
          >
            {doi}
          </a>
        )}
      </List.Content>

      <List.Content floated="right">
        <CopyButton
          text={item.links.self_html}
          size="tiny"
          className="cds-version mr-0"
          icon="linkify"
        />
      </List.Content>

      <List.Content floated="right">
        <small className={activeVersion ? "text-muted-darken" : "text-muted"}>
          {item.publication_date}
        </small>
      </List.Content>
    </List.Item>
  );
};

RecordVersionItemContent.propTypes = {
  item: PropTypes.object.isRequired,
  activeVersion: PropTypes.bool.isRequired,
  doi: PropTypes.string.isRequired,
};
