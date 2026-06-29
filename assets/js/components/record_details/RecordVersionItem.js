import React, { useMemo } from "react";
import { Icon, List } from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import PropTypes from "prop-types";
import { CopyButton } from "@js/invenio_app_rdm/components/CopyButton";

function readCommitteeApprovalData() {
  const el = document.getElementById("recordManagement");
  if (!el) return null;
  try {
    return JSON.parse(el.dataset.committeeApproval || "null");
  } catch (_) {
    return null;
  }
}

export const RecordVersionItemContent = ({ item, activeVersion, doi }) => {
  const committeeApproval = useMemo(readCommitteeApprovalData, []);

  // --- Internal draft side ---
  // committee_approval is the parent record's approval dict, shared by all versions.
  // Keys: reportnumber, approved_internal_version, approved_public_version,
  //       source_public_version (internal parent); source_internal_version (public parent).
  const ea = committeeApproval?.committee_approval || {};
  const approvedReportNumber = ea.reportnumber;
  // approved_internal_version: recid of the version that was submitted and approved.
  const isApprovedVersion =
    !!approvedReportNumber && ea.approved_internal_version === item.id;
  // source_public_version: recid of the internal version used to create the public record.
  const publicRecordId = ea.approved_public_version;

  const isPublicSourceVersion =
    !!publicRecordId && ea.source_public_version === item.id;
  // If approved and public-source are the same version, show only the public record link.
  const sameVersion = isApprovedVersion && isPublicSourceVersion;

  return (
    <List.Item
      key={item.id}
      {...(activeVersion && { className: "version active" })}
    >
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

        {doi && (
          <a
            href={`https://doi.org/${doi}`}
            className={
              "doi" + (activeVersion ? " text-muted-darken" : " text-muted")
            }
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
