"""
Compatibility utilities for testing with zgw-consumers 1.x

This module provides compatibility shims for testing utilities that moved
between zgw-consumers versions.

In zgw-consumers 1.x, test utilities moved from zgw_consumers.test to
zgw_consumers_oas package.
"""

from rest_framework import serializers
from zgw_consumers_oas import generate_oas_component, read_schema
from zgw_consumers_oas.mocks import mock_service_oas_get

__all__ = [
    "generate_oas_component",
    "mock_service_oas_get",
    "read_schema",
    "APIModelSerializer",
]


class APIModelSerializer(serializers.Serializer):
    """
    Backward compatibility shim for zgw_consumers.drf.serializers.APIModelSerializer.

    In zgw-consumers <1.0, this was a serializer that could work with API models
    (dataclasses with type hints). In zgw-consumers 1.x, this class was removed.

    This is a simple replacement that just extends DRF's Serializer. Subclasses
    must define their fields explicitly.
    """

    pass
