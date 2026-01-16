import React from "react";
import { List } from "semantic-ui-react";
import { i18next } from "@translations/invenio_app_rdm/i18next";
import PropTypes from "prop-types";
import { CopyButton } from "@js/invenio_app_rdm/components/CopyButton";

export const RecordVersionItemContent = ({ item, activeVersion, doi }) => {
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
