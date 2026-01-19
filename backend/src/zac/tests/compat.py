"""
Compatibility utilities for testing with zgw-consumers 1.x

This module provides compatibility shims for testing utilities that moved
between zgw-consumers versions.

In zgw-consumers 1.x:
- Test utilities moved from zgw_consumers.test to zgw_consumers_oas package
- APIModelSerializer was removed with suggestion to use djangorestframework-dataclasses

We follow the official recommendation and use djangorestframework-dataclasses.
"""

from rest_framework_dataclasses.serializers import DataclassSerializer
from zgw_consumers_oas import generate_oas_component, read_schema
from zgw_consumers_oas.mocks import mock_service_oas_get

__all__ = [
    "generate_oas_component",
    "mock_service_oas_get",
    "read_schema",
    "APIModelSerializer",
]

# Backward compatibility alias: APIModelSerializer -> DataclassSerializer
# Usage: Change Meta.model to Meta.dataclass in your serializers
APIModelSerializer = DataclassSerializer
