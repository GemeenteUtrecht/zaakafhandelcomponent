#!/bin/sh

set -e

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

until pg_isready; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Apply database migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

>&2 echo "Starting server"
cmd="uwsgi \
    --http :8000 \
    --module zac.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --processes 4 \
    --threads 1 \
    --buffer-size 32768 \
"

PY_AUTORELOAD=${AUTORELOAD:-false}
if [ $PY_AUTORELOAD = "true" ]
then
        >&2 echo "WARNING: Starting uwsgi with py-autoreload enabled is unsafe and should not be used outside development environments!"
        cmd="${cmd} --py-autoreload 1"
fi

# Start server
exec $cmd
