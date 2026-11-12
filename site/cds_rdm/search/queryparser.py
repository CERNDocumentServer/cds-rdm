# -*- coding: utf-8 -*-
#
# Copyright (C) 2026 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the GPL-2.0 License; see LICENSE file for more details.

"""Search configuration for the CDS record search bar.

Used with the upstream ``QueryParser`` (see ``invenio.cfg``)::

    QueryParser.factory(
        fields=DEFAULT_SEARCH_FIELDS,
        lenient=True,
        mapping={...},
        tree_transformer_cls=CDSSearchFieldTransformer,
    )
"""

import re

from invenio_records_resources.services.records.queryparser import (
    SearchFieldTransformer,
)
from luqum.tree import (
    AndOperation,
    Group,
    OrOperation,
    Phrase,
    Plus,
    Prohibit,
    Word,
)

DEFAULT_SEARCH_FIELDS = [
    # Mirrors ``index.query.default_field`` of the upstream record mapping
    # (invenio-rdm-records, rdmrecords/records/record-v7.0.0.json), with boosts.
    "id^10",
    "metadata.title^10",
    "metadata.title.original^10",
    "metadata.additional_titles.title^5",
    "metadata.creators.person_or_org.name^5",
    "metadata.creators.person_or_org.family_name^5",
    "metadata.creators.person_or_org.given_name^2",
    "metadata.creators.affiliations.name",
    "metadata.contributors.person_or_org.name^2",
    "metadata.contributors.person_or_org.family_name^2",
    "metadata.contributors.person_or_org.given_name",
    "metadata.contributors.affiliations.name",
    "metadata.identifiers.identifier^10",
    "metadata.subjects.subject^3",
    "metadata.description",
    "metadata.additional_descriptions.description",
    "metadata.contact",
    "metadata.formats",
    "metadata.funding.award.identifiers.identifier",
    "metadata.funding.award.acronym.text",
    "metadata.funding.award.number",
    "metadata.funding.funder.name",
    "metadata.locations.features.place",
    "metadata.locations.features.description",
    "metadata.publication_date",
    "metadata.publisher",
    "metadata.version",
    "metadata.dates.description",
    "metadata.references.reference",
    # Not in the upstream default fields.
    "pids.doi.identifier^10",
    "metadata.related_identifiers.identifier^3",
    "metadata.resource_type.title.en^3",
    "parent.communities.entries.metadata.title^2",
    "custom_fields.cern:experiments.title.en^2",
    "custom_fields.cern:accelerators.title.en^2",
    "custom_fields.cern:departments.title.en",
    "custom_fields.cern:programmes.title.en",
    "custom_fields.cern:beams.title.en",
    "custom_fields.cern:committees.title.en",
    "custom_fields.cern:projects",
    "custom_fields.cern:studies",
    "custom_fields.cern:facilities",
    "custom_fields.meeting:meeting.title",
    "custom_fields.journal:journal.title",
    "custom_fields.thesis:thesis.university",
]
"""Fields searched by a query without field qualifiers, with boosts.

Never use wildcards here: ``*`` would also search fields restricted to
administrators, such as ``internal_notes``.
"""

# A word the analyzer splits into several tokens: report numbers, DOIs,
# hyphenated words. Not words with wildcards or escapes.
_COMPOUND_WORD_RE = re.compile(r"^[^*?\\\"]+[-/][^*?\\\"]+$")


class CDSSearchFieldTransformer(SearchFieldTransformer):
    """Field aliases (upstream), plus: every word must match.

    OpenSearch's ``default_operator: AND`` is applied per field when the fields
    use different analyzers: ``thesis Mobius`` would need both words in the
    same field and match nothing. An explicit ``AND`` lets each word match in
    any field.
    """

    def visit_unknown_operation(self, node, context):
        """Turn ``a b`` into ``a AND b``, unless ``+``/``-`` say what is required."""
        children = list(self.clone_children(node, node.clone_item(), context))
        if any(isinstance(child, (Plus, Prohibit)) for child in children):
            new_node = node.clone_item()
            new_node.children = children
            yield new_node
            return
        # "a b OR c" is "a (b OR c)": keep the group, OpenSearch would read
        # "a AND b OR c" as "+a +b c".
        yield AndOperation(
            *(Group(c) if isinstance(c, OrOperation) else c for c in children)
        )

    def visit_word(self, node, context):
        """Search a word made of several tokens as a phrase.

        ``CERN-THESIS-2021-078`` must match as a whole, not any of its parts,
        and the ``/`` of a DOI would otherwise start a regular expression.
        """
        for new_node in super().visit_word(node, context):
            if isinstance(new_node, Word) and _COMPOUND_WORD_RE.match(new_node.value):
                new_node = Phrase(f'"{new_node.value}"')
            yield new_node
