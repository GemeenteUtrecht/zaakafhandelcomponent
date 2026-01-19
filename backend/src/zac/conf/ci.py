"""
Continuous integration settings module.
"""

import logging
import os

os.environ.setdefault("SECRET_KEY", "dummy")

from .includes.base import *  # noqa isort:skip

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    "axes": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "oas": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "oidc": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    # cache that resets itself after every request
    "request": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "request",
    },
}

LOGGING = None  # Quiet is nice
logging.disable(logging.CRITICAL)

#
# Django-axes
#
AXES_BEHIND_REVERSE_PROXY = False

DEBUG = False
TEMPLATE_DEBUG = False
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

ENVIRONMENT = "ci"
