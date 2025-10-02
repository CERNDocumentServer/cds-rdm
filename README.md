# CDS-RDM

The CDS-RDM instance based on [InvenioRDM](https://inveniordm.docs.cern.ch/).

## Install

Make sure that you have all the [prerequisites](https://inveniordm.docs.cern.ch/install/#1-install-the-cli-tool). Then run:

```
$ invenio-cli install
$ invenio-cli run
```

Now visit https://127.0.0.1:5000. For more detailed instructions, read the documentation [here](https://inveniordm.docs.cern.ch/install/).

## Create demo users

```
pipenv run invenio users create admin@demo.org --password 123456 --active --confirm
# grant superadmin access to a user
pipenv run invenio access allow superuser-access user admin@demo.org
```

## Deployment

### Update dependencies before deployment

To update dependencies before deployment, you need to run pipenv lock in the target deployment environment:

#### Run the container with x86_64 architecture
```s
docker run -it --platform="linux/amd64" --rm -v $(pwd):/app \
    registry.cern.ch/inveniosoftware/almalinux:1
```
#### Inside the container update the Pipfile.lock
```s
[root@3954486e4a37]# cd /app
[root@3954486e4a37]# pipenv lock
```
