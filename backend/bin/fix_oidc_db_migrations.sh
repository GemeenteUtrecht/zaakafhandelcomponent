#!/bin/sh
set -e

echo "🩹 [fix_oidc_db_migrations] Checking mozilla_django_oidc_db migration consistency..."

# Wait until DB is reachable through Django settings
until python src/manage.py dbshell -c "SELECT 1;" >/dev/null 2>&1; do
  echo "⏳ Waiting for database..."
  sleep 2
done

# Check if the OIDC table exists
TABLE_EXISTS=$(python src/manage.py dbshell -c \
  "SELECT to_regclass('public.mozilla_django_oidc_db_openidconnectconfig');" 2>/dev/null | grep -c mozilla_django_oidc_db_openidconnectconfig || true)

# Count migration rows
MIGRATION_COUNT=$(python src/manage.py dbshell -c \
  "SELECT COUNT(*) FROM django_migrations WHERE app='mozilla_django_oidc_db';" 2>/dev/null | grep -Eo '[0-9]+' || echo 0)

# Get actual migration names
MIGRATION_NAMES=$(python src/manage.py dbshell -c \
  "SELECT name FROM django_migrations WHERE app='mozilla_django_oidc_db';" 2>/dev/null | grep mozilla_django_oidc_db || true)

echo "🧩 Table exists: $TABLE_EXISTS | Migration rows: $MIGRATION_COUNT"

# Helper to replace all rows with the squashed one
reset_migration_rows() {
  echo "⚠️  Resetting mozilla_django_oidc_db migration history..."
  python src/manage.py dbshell <<'SQL'
DELETE FROM django_migrations WHERE app='mozilla_django_oidc_db';
INSERT INTO django_migrations (app, name, applied)
VALUES ('mozilla_django_oidc_db', '0001_initial_to_v023', NOW());
SQL
  echo "✅ Inserted squashed migration record (0001_initial_to_v023)."
}

# Decision tree
if [ "$TABLE_EXISTS" -eq 1 ] && [ "$MIGRATION_COUNT" -eq 0 ]; then
  echo "⚠️  Table exists but no migration history → correcting..."
  reset_migration_rows
  python src/manage.py migrate mozilla_django_oidc_db --fake || true

elif [ "$TABLE_EXISTS" -eq 1 ] && echo "$MIGRATION_NAMES" | grep -qv "0001_initial_to_v023"; then
  echo "⚠️  Outdated migration history detected → replacing with squashed version..."
  reset_migration_rows
  python src/manage.py migrate mozilla_django_oidc_db --fake || true

else
  echo "✅ No inconsistencies detected for mozilla_django_oidc_db."
fi

echo "✅ [fix_oidc_db_migrations] Completed."
