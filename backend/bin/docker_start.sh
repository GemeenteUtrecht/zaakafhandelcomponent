#!/bin/sh

set -e

###############################################################################
# Environment setup
###############################################################################
export PGHOST="${DB_HOST:-db}"
export PGPORT="${DB_PORT:-5432}"

UWSGI_PORT="${UWSGI_PORT:-8000}"
UWSGI_PROCESSES="${UWSGI_PROCESSES:-16}"
UWSGI_THREADS="${UWSGI_THREADS:-8}"
UWSGI_BUFFER_SIZE="${UWSGI_BUFFER_SIZE:-65536}"
UWSGI_MAX_REQUESTS="${UWSGI_MAX_REQUESTS:-5000}"
UWSGI_HARAKIRI="${UWSGI_HARAKIRI:-30}"

###############################################################################
# Wait for database availability
###############################################################################
echo "⏳ Waiting for PostgreSQL at ${PGHOST}:${PGPORT} ..."
until pg_isready -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1; do
  sleep 1
done
echo "✔ Database is reachable."

###############################################################################
# Fix OIDC migration inconsistencies BEFORE applying Django migrations
###############################################################################
echo "🔧 Running OIDC migration consistency fix..."
/fix_oidc_db_migrations.sh || echo "⚠️  OIDC fixer exited, continuing..."

###############################################################################
# Apply Django migrations
###############################################################################
echo "🛠  Applying Django migrations..."
python src/manage.py migrate --noinput

###############################################################################
# Generate OpenAPI schema
###############################################################################
echo "📄 Generating OpenAPI schema..."
python src/manage.py spectacular --file src/openapi.yaml

###############################################################################
# Start uWSGI
###############################################################################
echo "🚀 Starting uWSGI application server..."

CMD="uwsgi \
    --http :${UWSGI_PORT} \
    --module zac.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media \
    --chdir src \
    --processes ${UWSGI_PROCESSES} \
    --threads ${UWSGI_THREADS} \
    --buffer-size ${UWSGI_BUFFER_SIZE} \
    --enable-threads \
    --max-requests ${UWSGI_MAX_REQUESTS} \
    --harakiri ${UWSGI_HARAKIRI}
"

if [ "${AUTORELOAD:-false}" = "true" ]; then
    echo "⚠️  Autoreload ENABLED (not recommended for production)"
    CMD="${CMD} --py-autoreload 1"
fi

exec $CMD
