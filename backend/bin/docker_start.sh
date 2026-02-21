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
uwsgi_max_requests_delta=${UWSGI_MAX_REQUESTS_DELTA:-500}
uwsgi_harakiri=${UWSGI_HARAKIRI:-30}
uwsgi_listen=${UWSGI_LISTEN:-1024}
uwsgi_reload_on_rss=${UWSGI_RELOAD_ON_RSS:-400}

until pg_isready; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Apply database migrations
>&2 echo "Apply database migrations"
if [ "${FAKE_OIDC_MIGRATION}" = "true" ]; then
    >&2 echo "Dropping all mozilla_django_oidc_db tables and clearing migration history to allow a clean recreate..."
    python -c "
import os
import sys
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zac.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute('DROP TABLE IF EXISTS mozilla_django_oidc_db_oidcclient CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS mozilla_django_oidc_db_oidcprovider CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS mozilla_django_oidc_db_openidconnectconfig CASCADE;')
    cursor.execute('DROP TABLE IF EXISTS mozilla_django_oidc_db_openidconnectconfig_default_groups CASCADE;')
    cursor.execute(\"DELETE FROM django_migrations WHERE app = 'mozilla_django_oidc_db';\")
" || true
fi
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
    --py-call-uwsgi-fork-hooks \
    --max-requests $uwsgi_max_requests \
    --max-requests-delta $uwsgi_max_requests_delta \
    --harakiri $uwsgi_harakiri \
    --listen ${uwsgi_listen:-1024} \
    --reload-on-rss $uwsgi_reload_on_rss \

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
