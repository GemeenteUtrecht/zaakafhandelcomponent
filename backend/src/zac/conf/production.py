"""
Production environment settings module.

Tweaks the base settings so that caching mechanisms are used where possible,
and HTTPS is leveraged where possible to further secure things.
"""

import os

os.environ.setdefault("ENVIRONMENT", "production")

from .includes.base import *  # noqa isort:skip

os.environ.setdefault("DEBUG", "yes")
os.environ.setdefault("LOG_STDOUT", "yes")

conn_max_age = config("DB_CONN_MAX_AGE", cast=float, default=None)
for db_config in DATABASES.values():
    db_config["CONN_MAX_AGE"] = conn_max_age

# Caching sessions.
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"

# Caching templates.
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    ("django.template.loaders.cached.Loader", TEMPLATE_LOADERS)
]

# The file storage engine to use when collecting static files with the
# collectstatic management command.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        "OPTIONS": {
            "manifest_strict": False,
        },
    },
}

# Production logging facility.
# handlers = ["console"] if LOG_STDOUT else ["django"]

# LOGGING["loggers"].update(
#     {
#         "": {"handlers": handlers, "level": "ERROR", "propagate": False},
#         "django": {"handlers": handlers, "level": "INFO", "propagate": True},
#         "django.security.DisallowedHost": {
#             "handlers": handlers,
#             "level": "CRITICAL",
#             "propagate": False,
#         },
#     }
# )

# Only set this when we're behind a reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True  # Sets X-Content-Type-Options: nosniff

# Deal with being hosted on a subpath
subpath = config("SUBPATH", default=None)
if subpath:
    if not subpath.startswith("/"):
        subpath = f"/{subpath}"

    FORCE_SCRIPT_NAME = subpath
    STATIC_URL = f"{FORCE_SCRIPT_NAME}{STATIC_URL}"
    MEDIA_URL = f"{FORCE_SCRIPT_NAME}{MEDIA_URL}"

#
# Custom settings overrides
#
SHOW_ALERT = False

# Set up APM
ELASTIC_APM_SERVER_URL = config("ELASTIC_APM_SERVER_URL", None)
ELASTIC_APM = {
    "SERVICE_NAME": f"Zaakafhandelcomponent - {ENVIRONMENT}",
    "SECRET_TOKEN": config("ELASTIC_APM_SECRET_TOKEN", "default"),
    "SERVER_URL": ELASTIC_APM_SERVER_URL,
    "SERVER_TIMEOUT": "30s",
    "TRANSACTIONS_SAMPLE_RATE": 0.1,  # 10% of transactions
}
if not ELASTIC_APM_SERVER_URL:
    ELASTIC_APM["ENABLED"] = False
    ELASTIC_APM["SERVER_URL"] = "http://localhost:8200"
else:
    MIDDLEWARE = ["elasticapm.contrib.django.middleware.TracingMiddleware"] + MIDDLEWARE
    INSTALLED_APPS = INSTALLED_APPS + [
        "elasticapm.contrib.django",
    ]
