"""
Modern ZGW API Client for ZAC.

This package provides a modular, well-architected ZGW API client built on composition.

Main exports:
- ZGWClient: The main client class

Components (for advanced usage):
- SchemaLoader, SchemaRegistry: Schema management
- OperationResolver, OperationExecutor: Operation handling
- URLNormalizer: URL/path normalization
- PluralizationService: Dutch pluralization
- ResourceCRUD: CRUD operations
- ErrorHandler: Error handling
- BackwardCompatibilityMixin: Legacy API support
"""

from .client import ZGWClient

__all__ = ["ZGWClient"]
