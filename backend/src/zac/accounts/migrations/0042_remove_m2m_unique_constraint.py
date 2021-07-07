from django.db import migrations, connection


def get_constraint_name(apps, _):
    select_conname_sql = (
        "SELECT con.conname "
        "FROM pg_constraint con JOIN pg_class cl on con.conrelid = cl.oid "
        "WHERE relname = 'accounts_user_atomic_permissions' and contype = 'u' ;"
    )

    with connection.cursor() as cursor:
        # retrieve constraint name from DB
        cursor.execute(select_conname_sql)
        row = cursor.fetchone()

        if row:
            drop_constraint_sql = (
                f"ALTER TABLE accounts_user_atomic_permissions DROP CONSTRAINT {row[0]}"
            )
            cursor.execute(drop_constraint_sql)


class Migration(migrations.Migration):

    dependencies = [("accounts", "0041_auto_20210625_1124")]

    operations = [migrations.RunPython(get_constraint_name, migrations.RunPython.noop)]
