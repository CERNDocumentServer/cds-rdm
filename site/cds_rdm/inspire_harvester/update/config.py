from cds_rdm.inspire_harvester.update.fields.base import PreferCurrentMergeDictUpdate, \
    OverwriteFieldUpdate, ListOfDictAppendUniqueUpdate
from cds_rdm.inspire_harvester.update.fields.creatibutors import CreatibutorsFieldUpdate
from cds_rdm.inspire_harvester.update.fields.custom_fields import ThesisFieldUpdate
from cds_rdm.inspire_harvester.update.fields.identifiers import \
    RelatedIdentifiersUpdate, IdentifiersFieldUpdate
from cds_rdm.inspire_harvester.update.fields.metadata import PublicationDateUpdate

UPDATE_STRATEGY_CONFIG = {
    # fields not included in the strategy raise error on update attempt
    "pids": PreferCurrentMergeDictUpdate(keep_incoming_keys=[]),
    # "files": FilesUpdate(),
    "metadata.creators": CreatibutorsFieldUpdate(strict=True),
    "metadata.contributors": CreatibutorsFieldUpdate(strict=False),
    "metadata.identifiers": IdentifiersFieldUpdate(),
    "metadata.related_identifiers": RelatedIdentifiersUpdate(),
    "metadata.publication_date": PublicationDateUpdate(),
    "metadata.subjects":  ListOfDictAppendUniqueUpdate(key_field="subject"),
    "metadata.languages": ListOfDictAppendUniqueUpdate(key_field="id"),
    "metadata.description": OverwriteFieldUpdate(),
    "metadata.title": OverwriteFieldUpdate(),
    "custom_fields.thesis:thesis": ThesisFieldUpdate(),
    "custom_fields.cern:accelerators": ListOfDictAppendUniqueUpdate(key_field="id"),
    "custom_fields.cern:experiments": ListOfDictAppendUniqueUpdate(key_field="id"),
    # "custom_fields.cern:beams": IgnoreFieldUpdate(),
}