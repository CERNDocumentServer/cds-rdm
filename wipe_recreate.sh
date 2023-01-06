#!/usr/bin/env sh

# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

# Prompt to confirm action
read -r -p "Are you sure you want to wipe everything and create a new empty instance? [y/N] " response
if [[ ! ("$response" =~ ^([yY][eE][sS]|[yY])$) ]]
then
    exit 0
fi

# Wipe
# ----
invenio shell --no-term-title -c "import redis; redis.StrictRedis.from_url(app.config['CACHE_REDIS_URL']).flushall(); print('Cache cleared')"
# NOTE: db destroy is not needed since DB keeps being created
#       Just need to drop all tables from it.
invenio db drop --yes-i-know
invenio index destroy --force --yes-i-know
invenio index queue init purge

# Recreate
# --------
invenio db create
invenio files location create --default 'default-location' $(invenio shell --no-term-title -c "print(app.instance_path)")'/data'
invenio roles create admin
invenio access allow superuser-access role admin
invenio index init --force
invenio rdm-records custom-fields init
invenio communities custom-fields init

# Fixtures
# --------
invenio rdm-records fixtures
