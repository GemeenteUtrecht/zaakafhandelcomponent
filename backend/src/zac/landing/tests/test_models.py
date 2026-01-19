from django.test import TestCase

from .factories import (
    LandingPageConfigurationFactory,
    LandingPageLinkFactory,
    LandingPageSectionFactory,
)


class LandingPageConfigurationTestCase(TestCase):
    def test_create(self):
        LandingPageConfigurationFactory.create()

    def test_str(self):
        configuration = LandingPageConfigurationFactory.build(
            title="Startpagina Werkomgeving"
        )
        self.assertEqual("Startpagina Werkomgeving", str(configuration))


class LandingPageSectionTestCase(TestCase):
    def test_create(self):
        section = LandingPageSectionFactory.create()
        self.assertIn(section, section.landing_page_configuration.sections.all())

    def test_str(self):
        section = LandingPageSectionFactory.build(name="Processen en activiteiten")
        self.assertEqual("Processen en activiteiten", str(section))


class LandingPageLinkTestCase(TestCase):
    def test_create(self):
        link = LandingPageLinkFactory.create()
        self.assertFalse(link.landing_page_configuration)
        self.assertFalse(link.landing_page_section)

    def test_create_with_configuration(self):
        link = LandingPageLinkFactory.create(with_configuration=True)
        self.assertTrue(link.landing_page_configuration)
        self.assertIn(link, link.landing_page_configuration.links.all())

    def test_create_with_section(self):
        link = LandingPageLinkFactory.create(with_section=True)
        self.assertTrue(link.landing_page_section)
        self.assertIn(link, link.landing_page_section.links.all())

    def test_str(self):
        link = LandingPageLinkFactory.build(label="Nieuwe zaak starten")
        self.assertEqual("Nieuwe zaak starten", str(link))
