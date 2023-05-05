from django.db import migrations
from django.utils import timezone
from datetime import datetime


def set_default_user_auth_profile_end(apps, _):
    UserAuthorizationProfile = apps.get_model("accounts", "UserAuthorizationProfile")

    # migrate blueprint permission definitions
    for uap in UserAuthorizationProfile.objects.filter(end=None):
        uap.end = timezone.make_aware(datetime(2999, 12, 31))
        uap.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_alter_user_recently_viewed"),
    ]

    operations = [
        migrations.RunPython(set_default_user_auth_profile_end),
    ]
