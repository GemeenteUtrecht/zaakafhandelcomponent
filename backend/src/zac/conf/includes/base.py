import os

from django.urls import reverse_lazy

import sentry_sdk

from .utils import config, get_current_version, get_git_sha, get_sentry_integrations

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
)
BASE_DIR = os.path.abspath(
    os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir)
)

#
# Core Django settings
#
SITE_ID = config("SITE_ID", default=1)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# NEVER run with DEBUG=True in production-like environments
DEBUG = config("DEBUG", default=False)

# = domains we're running on
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", split=True)

IS_HTTPS = config("IS_HTTPS", default=not DEBUG)

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "nl"

TIME_ZONE = "UTC"  # note: this *may* affect the output of DRF datetimes

USE_I18N = True

USE_L10N = True

USE_TZ = True

USE_THOUSAND_SEPARATOR = True

#
# DATABASE and CACHING setup
#
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", "zac"),
        "USER": config("DB_USER", "zac"),
        "PASSWORD": config("DB_PASSWORD", "zac"),
        "HOST": config("DB_HOST", "localhost"),
        "PORT": config("DB_PORT", 5432),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_DEFAULT', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "axes": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_AXES', 'localhost:6379/0')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "oas": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_OAS', 'localhost:6379/1')}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{config('CACHE_SESSIONS', config('CACHE_OAS', 'localhost:6379/1'))}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
    # cache that resets itself after every request
    "request": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "request",
    },
}

# Application definition

INSTALLED_APPS = [
    # Note: contenttypes should be first, see Django ticket #10827
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    # Note: If enabled, at least one Site object is required
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Optional applications.
    "django_admin_index",
    "ordered_model",
    "django.contrib.admin",
    # 'django.contrib.admindocs',
    # 'django.contrib.humanize',
    # External applications.
    # organize admin
    "solo",
    "axes",
    "corsheaders",
    "sniplates",
    "zgw_consumers",
    "django_camunda",
    "import_export",
    "django_auth_adfs",
    "django_auth_adfs_db",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django_filters",
    "extra_views",
    "hijack",
    "compat",  # Part of hijack
    "hijack_admin",
    "django_better_admin_arrayfield",
    "django_scim",
    "nested_admin",
    # Project applications.
    "zac.elasticsearch",
    "zac.accounts",
    "zac.camunda",
    "zac.core",
    "zac.notifications",
    "zac.forms",
    "zac.landing",
    "zac.utils",
    "zac.contrib.board",
    "zac.contrib.brp",
    "zac.contrib.kadaster",
    "zac.contrib.kownsl",
    "zac.contrib.organisatieonderdelen",
    "zac.contrib.validsign.apps.ValidSignConfig",
    "zac.activities",
    "zac.contrib.dowc",
    "zac.contrib.objects.checklists",
    "zac.core.camunda.start_process",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # 'django.middleware.locale.LocaleMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "zac.accounts.scim.middleware.SCIMAuthMiddleware",
    "django_scim.middleware.SCIMAuthCheckMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "zac.accounts.middleware.HijackMiddleware",
    "zac.utils.middleware.ReleaseHeaderMiddleware",
]

ROOT_URLCONF = "zac.urls"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(DJANGO_PROJECT_DIR, "templates")],
        "APP_DIRS": False,  # conflicts with explicity specifying the loaders
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "zac.accounts.context_processors.user_serializer",
                "zac.utils.context_processors.settings",
            ],
            "loaders": TEMPLATE_LOADERS,
        },
    }
]

WSGI_APPLICATION = "zac.wsgi.application"

# Translations
LOCALE_PATHS = (os.path.join(DJANGO_PROJECT_DIR, "conf", "locale"),)

#
# SERVING of static and media files
#

STATIC_URL = "/static/"

STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Additional locations of static files
STATICFILES_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "static"),
    os.path.join(BASE_DIR, "node_modules", "font-awesome"),
]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

MEDIA_URL = "/media/"

DEFAULT_LOGO = f"{STATIC_URL}img/logo-placeholder.png"

#
# Sending EMAIL
#
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config(
    "EMAIL_PORT", default=25
)  # disabled on Google Cloud, use 487 instead
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False)
EMAIL_TIMEOUT = 10

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="zac@example.com")

#
# LOGGING
#
LOG_STDOUT = config("LOG_STDOUT", default=False)
LOG_LEVEL = config("LOG_LEVEL", default="INFO")
LOG_PERFORMANCE = config("LOG_PERFORMANCE", default=False)

LOGGING_DIR = os.path.join(BASE_DIR, "log")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(process)d %(thread)d  %(message)s"
        },
        "timestamped": {"format": "%(asctime)s %(levelname)s %(name)s  %(message)s"},
        "simple": {"format": "%(levelname)s  %(message)s"},
        "performance": {"format": "%(asctime)s %(process)d | %(thread)d | %(message)s"},
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "null": {"level": "DEBUG", "class": "logging.NullHandler"},
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "timestamped",
        },
        "django": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "django.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "project": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "zac.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 10,
        },
        "performance": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "performance",
        },
    },
    "loggers": {
        "zac": {
            "handlers": ["project"] if not LOG_STDOUT else ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.request": {
            "handlers": ["django"] if not LOG_STDOUT else ["console"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.template": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "performance": {
            "handlers": ["performance"] if LOG_PERFORMANCE else [],
            "level": "INFO",
            "propagate": False,
        },
    },
}

#
# AUTH settings - user accounts, passwords, backends...
#
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Allow logging in with both username+password and email+password
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    # authentication
    "django_auth_adfs_db.backends.AdfsAuthCodeBackend",
    "zac.accounts.backends.UserModelEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
    # authorization
    "zac.accounts.backends.PermissionsBackend",
]

SESSION_COOKIE_NAME = "zac_sessionid"

LOGIN_URL = reverse_lazy("accounts:login")
LOGIN_REDIRECT_URL = reverse_lazy("accounts:logged_in")

#
# SECURITY settings
#
SESSION_COOKIE_SECURE = IS_HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 12 * 60 * 60  # 12 hours

CSRF_COOKIE_SECURE = IS_HTTPS

X_FRAME_OPTIONS = "DENY"

#
# Custom settings
#
PROJECT_NAME = "zac"
SITE_TITLE = "Zaakafhandeling"

ENVIRONMENT = config("ENVIRONMENT", "")
SHOW_ALERT = True

##############################
#                            #
# 3RD PARTY LIBRARY SETTINGS #
#                            #
##############################

#
# DJANGO-AXES
#
AXES_CACHE = "axes"
AXES_LOGIN_FAILURE_LIMIT = 30  # Default: 3
AXES_LOCK_OUT_AT_FAILURE = True  # Default: True
AXES_USE_USER_AGENT = False  # Default: False
AXES_COOLOFF_TIME = 1  # One hour
AXES_BEHIND_REVERSE_PROXY = IS_HTTPS  # We have either Ingress or Nginx
AXES_ONLY_USER_FAILURES = (
    False  # Default: False (you might want to block on username rather than IP)
)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = (
    False  # Default: False (you might want to block on username and IP)
)

#
# CORS-HEADERS - see https://pypi.org/project/django-cors-headers/
#
# derive default value from debug yes/no - that enables it at dev-time but disables it
# in production-like environments
CORS_ALLOW_ALL_ORIGINS = config("CORS_HEADERS_ENABLED", default=DEBUG)
_angular_dev_server_port = config("ANGULAR_DEV_SERVER_PORT", default=4200)
CSRF_TRUSTED_ORIGINS = [
    f"localhost:{_angular_dev_server_port}",
    f"127.0.0.1:{_angular_dev_server_port}",
]

#
# DJANGO AUTH ADFS
#
AUTH_ADFS = {"SETTINGS_CLASS": "django_auth_adfs_db.settings.Settings"}

#
# DRF
#
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_SCHEMA_CLASS": "zac.api.schema.AutoSchema",
    "EXCEPTION_HANDLER": "zac.utils.exceptions.exception_handler",
}

#
# SPECTACULAR
#
SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api",
    "TITLE": "ZAC BFF",
    "DESCRIPTION": "Internal backend-for-frontend API documentation.",
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "drf_spectacular.contrib.djangorestframework_camel_case.camelize_serializer_fields",
        "zac.api.drf_spectacular.djangorestframework_camel_case.camelize_discriminators",
        "zac.api.drf_spectacular.component_titles.add_title_to_component_schema",
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "TOS": None,
    # Optional: MAY contain "name", "url", "email"
    "CONTACT": {
        "url": "https://github.com/GemeenteUtrecht/zaakafhandelcomponent",
    },
    # Optional: MUST contain "name", MAY contain URL
    "LICENSE": {"name": "EUPL-1.2"},
    "VERSION": "1.0.0",
    # Tags defined in the global scope
    "TAGS": [],
    # Optional: MUST contain 'url', may contain "description"
    "EXTERNAL_DOCS": {
        "url": "https://zaakafhandelcomponent.readthedocs.io/",
    },
    "ENUM_NAME_OVERRIDES": {
        "AardRelatieOmgekeerdeRichtingEnum": "zgw_consumers.api_models.constants.AardRelatieChoices",
        "VertrouwelijkheidaanduidingEnum": "zgw_consumers.api_models.constants.VertrouwelijkheidsAanduidingen",
    },
}

#
# Django-Admin-Index
#
ADMIN_INDEX_SHOW_REMAINING_APPS = True
ADMIN_INDEX_AUTO_CREATE_APP_GROUP = True
ADMIN_INDEX_HIDE_APP_INDEX_PAGES = True

# URLs from which DRF spectacular retrieves API schemas

EXTERNAL_API_SCHEMAS = {
    "BAG_API_SCHEMA": config(
        "BAG_API_SCHEMA",
        "https://api.bag.kadaster.nl/esd/huidigebevragingen/v1/openapi.yaml",
    ),
    "DOWC_API_SCHEMA": config(
        "DOWC_API_SCHEMA", "https://dowc.cg-intern.ont.utrecht.nl/api/v1"
    ),
    "KOWNSL_API_SCHEMA": config(
        "KOWNSL_API_SCHEMA",
        "https://kownsl.cg-intern.ont.utrecht.nl/api/v1",
    ),
    "OBJECTS_API_SCHEMA": config(
        "OBJECTS_API_SCHEMA",
        "https://objects.cg-intern.ont.utrecht.nl/api/v1",
    ),
    "OBJECTTYPES_API_SCHEMA": config(
        "OBJECTTYPES_API_SCHEMA",
        "https://objecttypes.cg-intern.ont.utrecht.nl/api/v1",
    ),
    "ZRC_API_SCHEMA": config(
        "ZRC_API_SCHEMA",
        "https://open-zaak.cg-intern.ont.utrecht.nl/zaken/api/v1/schema/openapi.json",
    ),
}

#
# SENTRY - error monitoring
#
SENTRY_DSN = config("SENTRY_DSN", None)

GIT_SHA: str = (
    get_git_sha()
)  # either pulled from the env (image build arg) or git filesystem
RELEASE = get_current_version()

if SENTRY_DSN:
    SENTRY_CONFIG = {
        "dsn": SENTRY_DSN,
        "environment": ENVIRONMENT,
        "release": RELEASE,
    }

    sentry_sdk.init(
        **SENTRY_CONFIG, integrations=get_sentry_integrations(), send_default_pii=True
    )

#
# ZGW-CONSUMERS
#
ZGW_CONSUMERS_CLIENT_CLASS = "zac.client.Client"
ZGW_CONSUMERS_TEST_SCHEMA_DIRS = [
    os.path.join(DJANGO_PROJECT_DIR, "tests", "schemas"),
    os.path.join(DJANGO_PROJECT_DIR, "contrib", "objects", "tests", "schemas"),
]

# Django-Hijack
HIJACK_LOGIN_REDIRECT_URL = "/ui"
HIJACK_LOGOUT_REDIRECT_URL = reverse_lazy("admin:accounts_user_changelist")
# The Admin mixin is used because we use a custom User-model.
HIJACK_REGISTER_ADMIN = False
# This is a CSRF-security risk.
# See: http://django-hijack.readthedocs.io/en/latest/configuration/#allowing-get-method-for-hijack-views
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_AUTHORIZE_STAFF = True
HIJACK_AUTHORIZE_STAFF_TO_HIJACK_STAFF = True
HIJACK_HEADER = "X-Is-Hijacked"


# ELASTICSEARCH CONFIG
ELASTICSEARCH_DSL = {
    "default": {"hosts": config("ES_HOST", "localhost:9200")},
}
ES_INDEX_ZAKEN = "zaken"
ES_INDEX_DOCUMENTEN = "documenten"
ES_INDEX_OBJECTEN = "objecten"
# USED FOR INDEXING EDGE NGRAM ANALYZER
MAX_GRAM = config("MAX_GRAM", 16)
MIN_GRAM = config("MIN_GRAM", 3)

# SCIM
SCIM_SERVICE_PROVIDER = {
    "NETLOC": config(
        "SCIM_NETLOC", default=ALLOWED_HOSTS[0] if ALLOWED_HOSTS else "localhost"
    ),
    "AUTHENTICATION_SCHEMES": [
        {
            "name": "API Key",
            "type": "apiKey",
            "description": "Authorization header with token",
            "documentationUrl": "https://zaakafhandelcomponent.readthedocs.io/en/latest/config.html",
        }
    ],
    "GROUP_ADAPTER": "zac.accounts.scim.adapters.AuthorizationProfileAdapter",
    "GROUP_MODEL": "zac.accounts.models.AuthorizationProfile",
    "USER_ADAPTER": "zac.accounts.scim.adapters.UserAdapter",
    "GROUP_FILTER_PARSER": "zac.accounts.scim.filters.AuthorizationProfileFilterQuery",
    "WWW_AUTHENTICATE_HEADER": "Token",
}

# Custom settings
UI_ROOT_URL = config("UI_ROOT_URL", default="/ui")
CREATE_ZAAK_PROCESS_DEFINITION_KEY = config(
    "CREATE_ZAAK_PROCESS_DEFINITION_KEY", default="zaak_aanmaken"
)
