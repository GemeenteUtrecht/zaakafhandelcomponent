"""
Shared test factories for ZAC.

This module provides factory_boy factories for commonly used models across
the ZAC test suite.
"""

import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

# Global counter for generating unique service slugs
_service_slug_counter = {}


def generate_service_slug(api_type: str) -> str:
    """
    Generate a unique slug for a Service based on its API type.

    This ensures each service gets a unique slug even when multiple services
    of the same type are created in the same test.
    """
    # Map API types to readable prefixes
    slug_prefixes = {
        APITypes.zrc: "zaken-api",
        APITypes.ztc: "catalogi-api",
        APITypes.drc: "documenten-api",
        APITypes.brc: "besluiten-api",
        APITypes.cmc: "contactmomenten-api",
        APITypes.kc: "klanten-api",
        APITypes.orc: "overige-api",
        APITypes.nrc: "notificaties-api",
    }
    prefix = slug_prefixes.get(api_type, "service")

    # Increment counter for this API type
    if prefix not in _service_slug_counter:
        _service_slug_counter[prefix] = 0
    _service_slug_counter[prefix] += 1

    return f"{prefix}-{_service_slug_counter[prefix]}"


class ServiceFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating zgw-consumers Service objects with unique slugs.

    The slug is automatically generated based on the API type, so you can
    simply pass api_type and api_root and get a properly slugged service.

    Usage:
        # Create a ZRC service - slug will be "zaken-api-1", "zaken-api-2", etc.
        service = ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        # Create multiple services with unique slugs
        zrc = ServiceFactory.create(api_type=APITypes.zrc)  # slug: "zaken-api-1"
        ztc = ServiceFactory.create(api_type=APITypes.ztc)  # slug: "catalogi-api-1"

        # Or use it as a drop-in replacement for Service.objects.create:
        # Before: Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        # After:  ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
    """

    class Meta:
        model = Service

    # Default to ZRC API type
    api_type = APITypes.zrc

    # Generate unique slugs based on API type
    slug = factory.LazyAttribute(lambda obj: generate_service_slug(obj.api_type))

    # Use faker for realistic API roots
    api_root = factory.Faker(
        "url",
        schemes=["https"],
    )

    # Optional: can be overridden
    label = factory.LazyAttribute(lambda obj: f"{obj.api_type} Service")

    # Set reasonable defaults for auth
    client_id = factory.Faker("uuid4")
    secret = factory.Faker("password", length=32)

    # Default to JWT auth
    auth_type = "zgw"

    # Default to no NLX
    nlx = ""

    # Default to no user info
    user_id = ""
    user_representation = ""
