#!/bin/sh
set -e

echo "🔧 [OIDC FIX] Checking mozilla_django_oidc_db migrations..."

DB_URI="sslmode=require host=${DB_HOST} port=${DB_PORT} dbname=${DB_NAME} user=${DB_USER} password=${DB_PASSWORD}"

psql_cmd="psql \"$DB_URI\" -qtAX"

###############################################
# 1. Check if the OIDC config table exists
###############################################
TABLE_EXISTS=$($psql_cmd <<'SQL'
SELECT CASE WHEN to_regclass('public.mozilla_django_oidc_db_openidconnectconfig') IS NULL
            THEN 0 ELSE 1 END;
SQL
)

###############################################
# 2. Check how many migration rows exist
###############################################
ROW_COUNT=$($psql_cmd <<'SQL'
SELECT COUNT(*) FROM django_migrations WHERE app='mozilla_django_oidc_db';
SQL
)

###############################################
# 3. Read actual migration names (if any)
###############################################
MIG_NAMES=$($psql_cmd <<'SQL'
SELECT name FROM django_migrations WHERE app='mozilla_django_oidc_db' ORDER BY name;
SQL
)

echo "🧩 Table exists: $TABLE_EXISTS | Migration rows: $ROW_COUNT"
echo "🧩 Migration names: ${MIG_NAMES:-<none>}"

###############################################
# Helper function: reset migration rows
###############################################
reset_rows() {
    echo "⚠️ Resetting OIDC migration history → applying squashed state"

    $psql_cmd <<'SQL'
DELETE FROM django_migrations WHERE app='mozilla_django_oidc_db';

INSERT INTO django_migrations (app, name, applied)
VALUES ('mozilla_django_oidc_db', '0001_initial_to_v023', NOW());
SQL

    echo "✅ Squashed migration recorded."
}

###############################################
# 4. Decision logic
###############################################

# Case A: Table exists but no migrations → broken state
if [ "$TABLE_EXISTS" -eq 1 ] && [ "$ROW_COUNT" -eq 0 ]; then
    echo "⚠️ Table exists but migration rows missing → repairing"
    reset_rows
    python src/manage.py migrate mozilla_django_oidc_db --fake
    echo "✅ Repaired state (A)."
    exit 0
fi

# Case B: Table exists + rows exist BUT not the squashed one
if [ "$TABLE_EXISTS" -eq 1 ] && ! printf "%s" "$MIG_NAMES" | grep -q "0001_initial_to_v023"; then
    echo "⚠️ Outdated / unsquashed migration history detected → replacing"
    reset_rows
    python src/manage.py migrate mozilla_django_oidc_db --fake
    echo "✅ Repaired state (B)."
    exit 0
fi

# Case C: Squashed migration present already → OK
if printf "%s" "$MIG_NAMES" | grep -q "0001_initial_to_v023"; then
    echo "✅ OIDC migration history already correct."
    exit 0
fi

# Fallback (should never trigger)
echo "⚠️ Unexpected OIDC migration state → no automatic fix applied."
exit 0
