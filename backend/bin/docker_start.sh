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
    # Inject missing columns that were skipped due to faking the squashed migration, so 0007 can read them.
    python -c "
import os
import sys
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zac.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'mozilla_django_oidc_db_openidconnectconfig');\")
    if not cursor.fetchone()[0]:
        sys.exit(0)

    columns = [
        ('oidc_op_logout_endpoint', 'varchar(1000) NOT NULL DEFAULT \'\''),
        ('oidc_token_use_basic_auth', 'boolean NOT NULL DEFAULT false'),
        ('oidc_use_nonce', 'boolean NOT NULL DEFAULT true'),
        ('oidc_nonce_size', 'integer NOT NULL DEFAULT 32'),
        ('oidc_state_size', 'integer NOT NULL DEFAULT 32'),
        ('oidc_keycloak_idp_hint', 'varchar(1000) NOT NULL DEFAULT \'\''),
        ('userinfo_claims_source', 'varchar(100) NOT NULL DEFAULT \'userinfo_endpoint\''),
        ('check_op_availability', 'boolean NOT NULL DEFAULT false'),
        ('superuser_group_names', 'varchar(50)[] NOT NULL DEFAULT \'{}\'::varchar[]'),
    ]
    for col_name, col_type in columns:
        cursor.execute(f'ALTER TABLE mozilla_django_oidc_db_openidconnectconfig ADD COLUMN IF NOT EXISTS {col_name} {col_type};')
" || true
    
    TABLE_EXISTS=$(python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'mozilla_django_oidc_db_openidconnectconfig');\"); print(cursor.fetchone()[0])" || echo "False")
    
    if [ "$TABLE_EXISTS" = "True" ]; then
        >&2 echo "Faking mozilla_django_oidc_db migration 0001_initial_to_v023 & 0006_oidcprovider_oidcclient to bypass DuplicateTable errors..."
        python src/manage.py migrate mozilla_django_oidc_db 0001_initial_to_v023 --fake || true
        python src/manage.py migrate mozilla_django_oidc_db 0006_oidcprovider_oidcclient --fake || true
    else
        >&2 echo "Table mozilla_django_oidc_db_openidconnectconfig does not exist. Skipping fake migration."
    fi
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
