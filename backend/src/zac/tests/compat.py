"""
Compatibility utilities for testing with zgw-consumers 1.x

This module provides compatibility shims for testing utilities that moved
between zgw-consumers versions.

In zgw-consumers 1.x:
- Test utilities moved from zgw_consumers.test to zgw_consumers_oas package
- APIModelSerializer was removed with suggestion to use djangorestframework-dataclasses

We follow the official recommendation and use djangorestframework-dataclasses.
"""

# Django 5.2 compatibility: timezone.utc was removed in favor of datetime.UTC
# Monkey-patch django.utils.timezone to add back utc for zgw_consumers_oas
from datetime import timezone as dt_timezone

from django.utils import timezone

from rest_framework_dataclasses.serializers import DataclassSerializer
from zgw_consumers_oas import read_schema
from zgw_consumers_oas.mocks import mock_service_oas_get

if not hasattr(timezone, "utc"):
    # Python 3.11+ has datetime.UTC, but Python 3.10 uses timezone.utc
    timezone.utc = dt_timezone.utc

# Now import generate_oas_component after patching
from zgw_consumers_oas import generate_oas_component

__all__ = [
    "generate_oas_component",
    "mock_service_oas_get",
    "read_schema",
    "DataclassSerializer",
]
