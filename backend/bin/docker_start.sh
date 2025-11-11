#!/bin/sh

set -e

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

uwsgi_port=${UWSGI_PORT:-8000}
uwsgi_processes=${UWSGI_PROCESSES:-16}
uwsgi_threads=${UWSGI_THREADS:-8}
uwsgi_buffer_size=${UWSGI_BUFFER_SIZE:-65536}
uwsgi_max_requests=${UWSGI_MAX_REQUESTS:-5000}
uwsgi_harakiri=${UWSGI_HARAKIRI:-30}

until pg_isready; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Run OIDC migration consistency fixer before global migrations
>&2 echo "Running mozilla_django_oidc_db migration consistency check..."
/app/src/zac/backend/bin/fix_oidc_db_migrations.sh || true

# Apply all migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

>&2 echo "Starting server"
cmd="uwsgi \
    --http :$uwsgi_port \
    --module zac.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --processes $uwsgi_processes \
    --threads $uwsgi_threads \
    --buffer-size $uwsgi_buffer_size \
    --enable-threads \
    --max-requests $uwsgi_max_requests \
    --harakiri $uwsgi_harakiri \
"

PY_AUTORELOAD=${AUTORELOAD:-false}
if [ $PY_AUTORELOAD = "true" ]
then
        >&2 echo "WARNING: Starting uwsgi with py-autoreload enabled is unsafe and should not be used outside development environments!"
        cmd="${cmd} --py-autoreload 1"
fi

# build openapi schema
python src/manage.py spectacular --file src/openapi.yaml

# Start server
exec $cmd
