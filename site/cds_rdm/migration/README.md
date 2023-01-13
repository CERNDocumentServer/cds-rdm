# Migration manual

## Dump a subset of records on legacy

```bash

inveniomigrator dump records -q '980:INTNOTECMSPUBL 980:NOTE -980:DELETED' --file-prefix cms-notes --latest-only --chunk-size=1000

```

## Define transforming models and rules resolution

You can adapt XML processing to different subsets of records by implementing different data models for each subset (f.e. collection).
Let's take CMS notes as an example:

```python

class CMSNote(CdsOverdo):
    """Translation Index for CDS Books."""

    __query__ = (
        '980__:INTNOTECMSPUBL 980__:NOTE'
    )

    __model_ignore_keys__ = {}

    _default_fields = {}



model = CMSNote(bases=(),
                entry_point_group="cds_rdm.migrator.rules"
                )

```

**query** - defines the MARC fields to which specific record should match. Attention: It does not recognise regexes that are used to specify the collection query in the admin interface of legacy CDS.

**__model_ignore_keys__** - set of keys to be ignored for this data model - fields will not be migrated

**bases** - by defining bases of models you can specify a parent model which fits all the subsets of records (f.e. 245 - title field MARC to JSON translation could be the same for all the models)

**entry_point_group** - reference to where the model should lookup for the set of the MARC translation rules, see the entrypoints below.

After defining your model and set of rules,you have to register them in the entrypoints of your application, in setup.cfg:

```editorconfig

[options.entry_points]
cds_rdm.migrator.models =
    cms_note = cds_rdm.migration.transform.models.note:model
cds_rdm.migrator.rules =
    base = cds_rdm.migration.transform.xml_processing.rules

```

## Run migration

All the commands should be run from cds-rdm project root, inside cds-rdm virtualenv.

Initialise an empty DB:

```
invenio-cli services setup --force --no-demo-data
```

Wait until all the fixtures are propagated and indexed.
Dump communities ids by running this script in `invenio shell`:

```python
import yaml
from pathlib import Path
from invenio_communities.communities.records.models import CommunityMetadata

community_map = {comm.slug: str(comm.id) for comm in CommunityMetadata.query.all()}
streams_path = str(Path('site/cds_rdm/migration/streams.yaml').absolute())
streams = {}

with open(streams_path, 'r') as fp:
    streams = yaml.safe_load(fp)

streams["records"]["load"]["cache"]["communities"] = community_map

with open(streams_path, 'w') as fp:
    yaml.safe_dump(streams, fp, default_flow_style=False)


```

Load the previously dumped legacy records. The configuration is already defined in streams.yaml - check the documentation of invenio-rdm-migrator for more details

```
invenio migration run
```

Once it has finished, run the re-indexing:

```
invenio rdm-records rebuild-index
```

Alternatively, you can index each resource separately:

Note that this step will strain your CPU rendering your laptop almost useless. In a `invenio-cli pyshell` run:

```python
# You might want to first run users, then rebuild index.
# Then run records and rebuild its index.
from invenio_access.permissions import system_identity
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_users_resources.proxies import current_users_service
current_users_service.rebuild_index(identity=system_identity)
current_rdm_records_service.rebuild_index(identity=system_identity)
```

- When the workers have no longer any tasks to run, in the _pyshell_ run:

```python
current_users_service.indexer.refresh()
current_rdm_records_service.indexer.refresh()
```

or if memory is an issue then you can generate the index batches with the code below

```
from invenio_rdm_records.proxies import current_rdm_records_service
from invenio_db import db

model_cls = current_rdm_records_service.record_cls.model_cls
records = db.session.query(model_cls.id).filter(
    model_cls.is_deleted == False,
).yield_per(1000)

current_rdm_records_service.indexer.bulk_index((rec.id for rec in records))
```
