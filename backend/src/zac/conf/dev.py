import os
import sys
import warnings

from .includes.environ import config

os.environ.setdefault("DEBUG", "yes")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
os.environ.setdefault(
    "SECRET_KEY", "kvilzgj7=*hi*1$nf2p-%&r*(@83q^wkdkb^^y#!(yaw=8_o!-"
)
os.environ.setdefault("IS_HTTPS", "no")

# uses postgresql by default, see base.py
os.environ.setdefault("DB_NAME", "zac")
os.environ.setdefault("DB_USER", "zac")
os.environ.setdefault("DB_PASSWORD", "zac")

os.environ.setdefault("LOG_STDOUT", "yes")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

from .includes.base import *  # noqa isort:skip

#
# Standard Django settings.
#
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["loggers"].update(
    {
        "django": {"handlers": ["console"], "level": "DEBUG", "propagate": True},
        "django.db.backends": {
            "handlers": ["django"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "performance": {"handlers": ["console"], "level": "INFO", "propagate": True},
    }
)

#
# Library settings
#

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += (
    "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
)


# Django debug toolbar
INSTALLED_APPS = ["debug_toolbar", "ddt_api_calls"] + INSTALLED_APPS
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
INTERNAL_IPS = ("127.0.0.1",)
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}
DEBUG_TOOLBAR_PANELS = [
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.logging.LoggingPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
    "ddt_api_calls.panels.APICallsPanel",
]

AXES_BEHIND_REVERSE_PROXY = (
    False  # Default: False (we are typically using Nginx as reverse proxy)
)

# in memory cache and django-axes don't get along.
# https://django-axes.readthedocs.io/en/latest/configuration.html#known-configuration-problems
if not config("USE_REDIS_CACHE", default=False):
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
        "oas": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "request": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "request",
        },
    }

# THOU SHALT NOT USE NAIVE DATETIMES
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

#
# Custom settings
#
ENVIRONMENT = "development"

if "test" in sys.argv:
    ES_INDEX_ZAKEN = "zaken_test"
    ES_INDEX_DOCUMENTEN = "documenten_test"
    ES_INDEX_OBJECTEN = "objecten_test"


# Override settings with local settings.
try:
    from .local import *  # noqa
except ImportError:
    pass
