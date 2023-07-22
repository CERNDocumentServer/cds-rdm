# CDS-RDM

The CDS-RDM instance based on [InvenioRDM](https://inveniordm.docs.cern.ch/).

### Update dependencies before deployment

To update dependencies before deployment, you need to run pipenv lock in the target deployment environment:

#### Run the container with x86_64 architecture
docker run -it --platform="linux/amd64" --rm -v $(pwd):/app \
    registry.cern.ch/inveniosoftware/almalinux:1

#### Inside the container update the Pipfile.lock
[root@3954486e4a37]# cd /app
[root@3954486e4a37]# pipenv lock
