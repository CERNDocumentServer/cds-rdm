# CDS-RDM

The CDS-RDM instance based on [InvenioRDM](https://inveniordm.docs.cern.ch/).

## Install

Install [uv](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer), and then run the following commands:

```bash
uv tool install invenio-cli
invenio-cli check-requirements --development
invenio-cli install
invenio-cli services setup
invenio-cli run
```

Now visit https://127.0.0.1:5000.

## Create demo users

```
uv run invenio users create admin@demo.org --password 123456 --active --confirm
# grant superadmin access to a user
uv run invenio access allow superuser-access user admin@demo.org
```

## Deployment

### Update dependencies before deployment

To update dependencies before deployment, run:

1. Run `invenio-cli packages lock`
2. Commit the updated `uv.lock`
