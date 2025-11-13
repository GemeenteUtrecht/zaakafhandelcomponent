#!/bin/sh
set -e

echo "🔧 [OIDC FIX] Checking mozilla_django_oidc_db migrations..."

# Basic sanity: require DB connection env
: "${DB_HOST:?DB_HOST not set}"
: "${DB_PORT:?DB_PORT not set}"
: "${DB_NAME:?DB_NAME not set}"
: "${DB_USER:?DB_USER not set}"
: "${DB_PASSWORD:?DB_PASSWORD not set}"

export PGPASSWORD="${DB_PASSWORD}"

psql_cmd() {
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -qtAX -c "$1"
}

###############################################
# 1. Ensure django_migrations table itself exists
###############################################
HAS_DJANGO_MIGRATIONS="$(psql_cmd "SELECT CASE WHEN to_regclass('public.django_migrations') IS NULL THEN 0 ELSE 1 END;")"

if [ "$HAS_DJANGO_MIGRATIONS" -ne 1 ] 2>/dev/null; then
    echo "ℹ️  django_migrations table does not exist yet – fresh DB, skipping OIDC fix."
    exit 0
fi

###############################################
# 2. Check if the OIDC config table exists
###############################################
TABLE_EXISTS="$(psql_cmd "SELECT CASE WHEN to_regclass('public.mozilla_django_oidc_db_openidconnectconfig') IS NULL THEN 0 ELSE 1 END;")"

if [ "$TABLE_EXISTS" -ne 1 ] 2>/dev/null; then
    echo "ℹ️  OIDC config table does not exist – nothing to repair."
    exit 0
fi

###############################################
# 3. Inspect current migration rows for this app
###############################################
ROW_COUNT="$(psql_cmd "SELECT COUNT(*) FROM django_migrations WHERE app='mozilla_django_oidc_db';")"

echo "🧩 OIDC table exists. Current migration row count: ${ROW_COUNT}"

# If we already have exactly the squashed migration, we still normalize but it's a no-op
MIG_NAMES="$(psql_cmd "SELECT name FROM django_migrations WHERE app='mozilla_django_oidc_db' ORDER BY name;")"
echo "🧩 Existing migration names (before fix):"
[ -n "$MIG_NAMES" ] && echo "$MIG_NAMES" || echo "<none>"

###############################################
# 4. ALWAYS enforce the squashed state when table exists
###############################################
echo "⚠️  Enforcing squashed migration state for mozilla_django_oidc_db..."

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -qtAX <<'SQL'
DELETE FROM django_migrations
WHERE app = 'mozilla_django_oidc_db';

INSERT INTO django_migrations (app, name, applied)
VALUES ('mozilla_django_oidc_db', '0001_initial_to_v023', NOW());
SQL

echo "✅ Squashed migration recorded as the only OIDC migration row."

###############################################
# 5. Show final state for logging
###############################################
FINAL_NAMES="$(psql_cmd "SELECT name FROM django_migrations WHERE app='mozilla_django_oidc_db' ORDER BY name;")"
echo "🧩 Final mozilla_django_oidc_db migrations:"
echo "$FINAL_NAMES"

echo "✅ [OIDC FIX] Completed."
exit 0
