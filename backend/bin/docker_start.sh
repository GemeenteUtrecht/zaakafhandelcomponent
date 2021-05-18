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

# Start server
>&2 echo "Starting server"
exec uwsgi \
    --http :8000 \
    --module zac.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --processes 4 \
    --threads 1 \
    --buffer-size=32k
    # processes & threads are needed for concurrency without nginx sitting inbetween
    # the buffer size increase is required because the ADFS token exchange returns
    # larger request block sizes than the default of 4k (5.1k)
