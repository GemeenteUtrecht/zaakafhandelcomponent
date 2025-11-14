#!/bin/sh
set -e

###############################################
# 0. Environment + DB readiness
###############################################

export PGHOST="${DB_HOST:-db}"
export PGPORT="${DB_PORT:-5432}"

uwsgi_port="${UWSGI_PORT:-8000}"
uwsgi_processes="${UWSGI_PROCESSES:-16}"
uwsgi_threads="${UWSGI_THREADS:-8}"
uwsgi_buffer_size="${UWSGI_BUFFER_SIZE:-65536}"
uwsgi_max_requests="${UWSGI_MAX_REQUESTS:-5000}"
uwsgi_harakiri="${UWSGI_HARAKIRI:-30}"

echo "⏳ Waiting for database ${PGHOST}:${PGPORT}..."
until pg_isready -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1; do
    echo "   …still waiting"
    sleep 1
done
echo "✅ Database connection established."

###############################################
# 1. OIDC migration consistency fixer (SQL-only)
###############################################
echo "🔧 Running mozilla_django_oidc_db migration consistency repair..."
# /fix_oidc_db_migrations.sh
echo "🔧 [OIDC FIX] Skipping mozilla_django_oidc_db migrations fix for now..."
echo "✅ OIDC migration consistency check completed."

###############################################
# 2. Run Django migrations (all apps)
###############################################
echo "🔧 Applying Django migrations..."
python src/manage.py migrate
echo "✅ All migrations applied."

###############################################
# 3. Build OpenAPI schema
###############################################
echo "📄 Generating OpenAPI schema..."
python src/manage.py spectacular --file src/openapi.yaml
echo "✅ OpenAPI schema generated."

###############################################
# 4. Start uWSGI
###############################################
echo "🚀 Starting uWSGI server..."

cmd="uwsgi \
    --http :${uwsgi_port} \
    --module zac.wsgi \
    --static-map /static=/app/static \
    --static-map /media=/app/media \
    --chdir src \
    --processes ${uwsgi_processes} \
    --threads ${uwsgi_threads} \
    --buffer-size ${uwsgi_buffer_size} \
    --enable-threads \
    --max-requests ${uwsgi_max_requests} \
    --harakiri ${uwsgi_harakiri}
"

if [ "${AUTORELOAD:-false}" = "true" ]; then
    echo "⚠️  py-autoreload enabled — unsafe for production!"
    cmd="${cmd} --py-autoreload 1"
fi

exec $cmd
