"""
Dutch pluralization service for ZGW API resource names.

This module provides utilities for converting between singular and plural
forms of Dutch resource names used in ZGW (Zaakgericht Werken) APIs.
"""


class PluralizationService:
    """
    Service for pluralizing Dutch words commonly used in ZGW APIs.

    This handles common patterns in ZGW API resource names, including
    special cases for Dutch pluralization rules.
    """

    # Mapping from singular to plural forms
    PLURALIZATION_MAP = {
        "catalogus": "catalogussen",
        "status": "statussen",
        "resultaat": "resultaten",
        "zaak": "zaken",
        "zaaktype": "zaaktypen",
        "statustype": "statustypen",
        "resultaattype": "resultaattypen",
        "roltype": "roltypen",
        "rol": "rollen",
        "eigenschap": "eigenschappen",
        "zaakeigenschap": "zaakeigenschappen",
        "object": "objecten",
        "objecttype": "objecttypen",
        "besluit": "besluiten",
        "besluittype": "besluittypen",
        "document": "documenten",
        "enkelvoudiginformatieobject": "enkelvoudiginformatieobjecten",
        "zaakinformatieobject": "zaakinformatieobjecten",
        "besluitinformatieobject": "besluitinformatieobjecten",
        "zaakobject": "zaakobjecten",
        "klantcontact": "klantcontacten",
    }

    # Reverse mapping from plural to singular forms
    SINGULARIZATION_MAP = {v: k for k, v in PLURALIZATION_MAP.items()}

    def pluralize(self, word: str) -> str:
        """
        Pluralize a Dutch word commonly used in ZGW APIs.

        If the word is already plural, it returns it unchanged.

        Args:
            word: The singular form of the word

        Returns:
            The plural form of the word

        Examples:
            >>> service = PluralizationService()
            >>> service.pluralize("zaak")
            'zaken'
            >>> service.pluralize("zaken")  # Already plural
            'zaken'
            >>> service.pluralize("catalogus")
            'catalogussen'
        """
        word_lower = word.lower()

        # If already plural, return as-is
        if word_lower in self.SINGULARIZATION_MAP:
            return word

        # Check if we have a specific singular->plural mapping
        if word_lower in self.PLURALIZATION_MAP:
            return self.PLURALIZATION_MAP[word_lower]

        # Check if it already looks plural (ends with common plural endings)
        if word.endswith(("en", "s")):
            return word

        # Default: just add 'en' (common Dutch plural)
        return f"{word}en"

    def singularize(self, word: str) -> str:
        """
        Singularize a Dutch word commonly used in ZGW APIs.

        If the word is already singular, it returns it unchanged.

        Args:
            word: The plural form of the word

        Returns:
            The singular form of the word

        Examples:
            >>> service = PluralizationService()
            >>> service.singularize("zaken")
            'zaak'
            >>> service.singularize("zaak")  # Already singular
            'zaak'
            >>> service.singularize("catalogussen")
            'catalogus'
        """
        word_lower = word.lower()

        # If already singular, return as-is
        if word_lower in self.PLURALIZATION_MAP:
            return word

        # Check if we have a specific plural->singular mapping
        if word_lower in self.SINGULARIZATION_MAP:
            return self.SINGULARIZATION_MAP[word_lower]

        # For unknown words, try removing common plural endings
        if word.endswith("en") and len(word) > 2:
            return word[:-2]

        if word.endswith("s") and len(word) > 1:
            return word[:-1]

        # If we can't singularize, return as-is
        return word
