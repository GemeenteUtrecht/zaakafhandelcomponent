from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class NonStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """
    ManifestStaticFilesStorage with manifest_strict disabled.

    This prevents errors when referenced static files are missing from the manifest,
    which can happen during development or when third-party packages reference
    files that don't exist.
    """

    manifest_strict = False
