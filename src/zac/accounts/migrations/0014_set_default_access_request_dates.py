from django.db import migrations
from datetime import date, timedelta
from ..constants import AccessRequestResult


def set_dates(apps, _):
    AccessRequest = apps.get_model("accounts", "AccessRequest")

    for access_request in AccessRequest.objects.filter(
        result=AccessRequestResult.approve
    ):
        access_request.start_date = date.today()
        # set default access for 1 week
        access_request.end_date = date.today() + timedelta(weeks=1)
        access_request.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_auto_20200923_1219"),
    ]

    operations = [
        migrations.RunPython(set_dates, migrations.RunPython.noop),
    ]
