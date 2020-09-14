from typing import Any, Dict

from django.conf import settings as django_settings


def settings(request) -> Dict[str, Any]:
    public_settings = (
        "GOOGLE_ANALYTICS_ID",
        "ENVIRONMENT",
        "SHOW_ALERT",
        "PROJECT_NAME",
        "ALFRESCO_USERNAME",
        "ALFRESCO_PASSWORD",
    )

    return {
        "settings": dict(
            [(k, getattr(django_settings, k, None)) for k in public_settings]
        )
    }
