#!/bin/sh
set -e

echo "[fix_oidc_db_migrations] Checking mozilla_django_oidc_db migration state..."

PSQL="psql \"sslmode=require host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER password=$DB_PASSWORD\" -v ON_ERROR_STOP=1 -tAc"

# Check if the real table exists
TABLE_EXISTS=$($PSQL "SELECT to_regclass('public.mozilla_django_oidc_db_openidconnectconfig') IS NOT NULL;")

# Check if squashed migration is recorded
HAS_SQUASH=$($PSQL "SELECT EXISTS(SELECT 1 FROM django_migrations WHERE app='mozilla_django_oidc_db' AND name='0001_initial_to_v023');")

echo "Table exists: $TABLE_EXISTS | Squashed migration present: $HAS_SQUASH"

if [ "$TABLE_EXISTS" = "t" ] && [ "$HAS_SQUASH" = "f" ]; then
  echo "OIDC table exists but squashed migration missing — fixing…"
  $PSQL "DELETE FROM django_migrations WHERE app='mozilla_django_oidc_db';"
  $PSQL "INSERT INTO django_migrations (app, name, applied)
         VALUES ('mozilla_django_oidc_db', '0001_initial_to_v023', NOW());"
  echo "Patched migration history."
else
  echo "No action required."
fi

echo "[fix_oidc_db_migrations] Done."
