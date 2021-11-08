import logging
from shutil import which
from subprocess import CalledProcessError, check_output

from decouple import Csv, config as _config, undefined
from sentry_sdk.integrations import DidNotEnable, django, redis

logger = logging.getLogger(__name__)


def config(option: str, default=undefined, *args, **kwargs):
    """
    Pull a config parameter from the environment.

    Read the config variable ``option``. If it's optional, use the ``default`` value.
    Input is automatically cast to the correct type, where the type is derived from the
    default value if possible.

    Pass ``split=True`` to split the comma-separated input into a list.
    """
    if "split" in kwargs:
        kwargs.pop("split")
        kwargs["cast"] = Csv()

    if default is not undefined and default is not None:
        kwargs.setdefault("cast", type(default))
    return _config(option, default=default, *args, **kwargs)


def get_sentry_integrations() -> list:
    """
    Determine which Sentry SDK integrations to enable.
    """
    default = [
        django.DjangoIntegration(),
        redis.RedisIntegration(),
    ]
    extra = []

    try:
        from sentry_sdk.integrations import celery
    except DidNotEnable:  # happens if the celery import fails by the integration
        pass
    else:
        extra.append(celery.CeleryIntegration())

    return [*default, *extra]


def _get_version_from_git():
    """
    Returns the current tag or commit hash supplied by git
    """
    try:
        tags = check_output(
            ["git", "tag", "--points-at", "HEAD"], universal_newlines=True
        )
    except CalledProcessError:
        logger.warning("Unable to list tags")
        tags = None

    if tags:
        return next(version for version in tags.splitlines())

    try:
        commit = check_output(["git", "rev-parse", "HEAD"], universal_newlines=True)
    except CalledProcessError:
        logger.warning("Unable to list current commit hash")
        commit = None

    return (commit or "").strip()


def get_current_version():
    version = config("VERSION_TAG", default=None)

    if version:
        return version
    elif which("git"):
        return _get_version_from_git()
    return ""


def get_git_sha() -> str:
    git_sha = config("GIT_SHA", default=None)
    if git_sha is not None:
        return git_sha
    return _get_version_from_git()
