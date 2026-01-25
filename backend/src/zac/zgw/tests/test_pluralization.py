"""
Unit tests for PluralizationService.
"""

from django.test import TestCase

from zac.zgw.operations.pluralization import PluralizationService


class PluralizationServiceTests(TestCase):
    """Tests for the PluralizationService class."""

    def setUp(self):
        self.service = PluralizationService()

    def test_pluralize_known_words(self):
        """Test pluralization of words in the mapping."""
        test_cases = {
            "zaak": "zaken",
            "catalogus": "catalogussen",
            "status": "statussen",
            "resultaat": "resultaten",
            "zaaktype": "zaaktypen",
            "rol": "rollen",
            "eigenschap": "eigenschappen",
            "object": "objecten",
            "besluit": "besluiten",
            "document": "documenten",
            "enkelvoudiginformatieobject": "enkelvoudiginformatieobjecten",
            "klantcontact": "klantcontacten",
        }

        for singular, expected_plural in test_cases.items():
            with self.subTest(word=singular):
                result = self.service.pluralize(singular)
                self.assertEqual(result, expected_plural)

    def test_pluralize_already_plural(self):
        """Test that plural words are returned unchanged."""
        plural_words = [
            "zaken",
            "catalogussen",
            "statussen",
            "resultaten",
            "zaaktypen",
            "rollen",
            "eigenschappen",
            "objecten",
            "besluiten",
            "documenten",
        ]

        for word in plural_words:
            with self.subTest(word=word):
                result = self.service.pluralize(word)
                self.assertEqual(result, word)

    def test_pluralize_unknown_word(self):
        """Test pluralization of unknown words with default rule."""
        # Words not in mapping should get 'en' added
        result = self.service.pluralize("test")
        self.assertEqual(result, "testen")

        # Words already ending in 'en' should be unchanged
        result = self.service.pluralize("testen")
        self.assertEqual(result, "testen")

        # Words ending in 's' should be unchanged
        result = self.service.pluralize("tests")
        self.assertEqual(result, "tests")

    def test_singularize_known_words(self):
        """Test singularization of words in the reverse mapping."""
        test_cases = {
            "zaken": "zaak",
            "catalogussen": "catalogus",
            "statussen": "status",
            "resultaten": "resultaat",
            "zaaktypen": "zaaktype",
            "rollen": "rol",
            "eigenschappen": "eigenschap",
            "objecten": "object",
            "besluiten": "besluit",
            "documenten": "document",
            "enkelvoudiginformatieobjecten": "enkelvoudiginformatieobject",
            "klantcontacten": "klantcontact",
        }

        for plural, expected_singular in test_cases.items():
            with self.subTest(word=plural):
                result = self.service.singularize(plural)
                self.assertEqual(result, expected_singular)

    def test_singularize_already_singular(self):
        """Test that singular words are returned unchanged."""
        singular_words = [
            "zaak",
            "catalogus",
            "status",
            "resultaat",
            "zaaktype",
            "rol",
            "eigenschap",
            "object",
            "besluit",
            "document",
        ]

        for word in singular_words:
            with self.subTest(word=word):
                result = self.service.singularize(word)
                self.assertEqual(result, word)

    def test_singularize_unknown_word(self):
        """Test singularization of unknown words with default rules."""
        # Words ending in 'en' should have it removed
        result = self.service.singularize("testen")
        self.assertEqual(result, "test")

        # Words ending in 's' should have it removed
        result = self.service.singularize("tests")
        self.assertEqual(result, "test")

        # Short words (less than 2 chars with 'en') should be unchanged
        result = self.service.singularize("en")
        self.assertEqual(result, "en")

    def test_case_insensitivity(self):
        """Test that pluralization handles different cases correctly."""
        # Lowercase should work
        result = self.service.pluralize("zaak")
        self.assertEqual(result, "zaken")

        # Pluralization works case-insensitively
        result = self.service.pluralize("Zaak")
        self.assertEqual(result, "zaken")  # Pluralized using lowercase mapping

    def test_round_trip(self):
        """Test that pluralize and singularize are inverses for known words."""
        test_words = [
            "zaak",
            "catalogus",
            "status",
            "resultaat",
            "zaaktype",
            "rol",
            "eigenschap",
            "object",
            "besluit",
            "document",
        ]

        for word in test_words:
            with self.subTest(word=word):
                plural = self.service.pluralize(word)
                result = self.service.singularize(plural)
                self.assertEqual(result, word)
