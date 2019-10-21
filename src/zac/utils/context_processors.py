from typing import Dict

from django.conf import settings as django_settings

from zds_client import Client
from zds_client.log import Log


def settings(request):
    public_settings = ('GOOGLE_ANALYTICS_ID', 'ENVIRONMENT',
                       'SHOW_ALERT', 'PROJECT_NAME')

    return {
        'settings': dict([
            (k, getattr(django_settings, k, None)) for k in public_settings
        ]),
    }


def client_log(request) -> Dict[str, Log]:
    log = Client._log
    total_duration = sum(entry.get("duration", 0) for entry in log.entries())
    return {"client_log": log, "total_duration_api_calls": total_duration}
