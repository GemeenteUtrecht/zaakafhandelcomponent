from django.test import RequestFactory, TestCase

from ...api.serializers import (
    LandingPageConfigurationSerializer,
    LandingPageLinkSerializer,
    LandingPageSectionSerializer,
)
from ..factories import (
    LandingPageConfigurationFactory,
    LandingPageLinkFactory,
    LandingPageSectionFactory,
)


class LandingPageConfigurationSerializerTestCase(TestCase):
    def test_data(self):
        configuration = LandingPageConfigurationFactory.create(
            title="Startpagina Werkomgeving"
        )
        request_factory = RequestFactory()
        request = request_factory.get("/")
        serializer = LandingPageConfigurationSerializer(configuration, request=request)
        data = serializer.data

        self.assertEqual("Startpagina Werkomgeving", data["title"])
        self.assertIn("http://testserver/media/example", data["image"])

    def test_data_nested(self):
        configuration = LandingPageConfigurationFactory.create(
            title="Startpagina Werkomgeving"
        )
        configuration.links.set(
            LandingPageLinkFactory.create_batch(
                3, label="Kik Intranet", href="http://www.example.com"
            )
        )

        # FIXME
        configuration.sections.set(
            (
                LandingPageSectionFactory._meta.model.objects.create(
                    name="Processen en activiteiten",
                    icon="account_tree",
                    landing_page_configuration=configuration,
                ),
            )
        )

        for section in configuration.sections.all():
            section.links.set(
                LandingPageLinkFactory.create_batch(
                    3,
                    icon="post_add",
                    label="Nieuwe taak starten",
                    href="/zaak-starten",
                )
            )

        request_factory = RequestFactory()
        request = request_factory.get("/")
        serializer = LandingPageConfigurationSerializer(configuration, request=request)
        data = serializer.data

        self.assertEqual("Startpagina Werkomgeving", data["title"])
        self.assertIn("http://testserver/media/example", data["image"])
        self.assertEqual("Processen en activiteiten", data["sections"][0]["name"])
        self.assertEqual("account_tree", data["sections"][0]["icon"])
        self.assertEqual(
            "Nieuwe taak starten", data["sections"][0]["links"][0]["label"]
        )
        self.assertEqual("/zaak-starten", data["sections"][0]["links"][0]["href"])
        self.assertEqual("Kik Intranet", data["links"][0]["label"])
        self.assertEqual("http://www.example.com", data["links"][0]["href"])


class LandingPageSectionSerializerTestCase(TestCase):
    def test_data(self):
        section = LandingPageSectionFactory.create(
            name="Processen en activiteiten", icon="account_tree"
        )
        serializer = LandingPageSectionSerializer(section)
        data = serializer.data

        self.assertEqual("Processen en activiteiten", data["name"])
        self.assertEqual("account_tree", data["icon"])

    def test_data_nested(self):
        section = LandingPageSectionFactory.create(
            name="Processen en activiteiten", icon="account_tree"
        )
        section.links.set(
            LandingPageLinkFactory.create_batch(
                3, icon="post_add", label="Nieuwe taak starten", href="/zaak-starten"
            )
        )
        serializer = LandingPageSectionSerializer(section)
        data = serializer.data

        self.assertEqual("Processen en activiteiten", data["name"])
        self.assertEqual("account_tree", data["icon"])
        self.assertEqual("Nieuwe taak starten", data["links"][0]["label"])
        self.assertEqual("/zaak-starten", data["links"][0]["href"])


class LandingPageLinkSerializerTestCase(TestCase):
    def test_data(self):
        link = LandingPageLinkFactory.create(label="Kik Intranet", href="#")
        serializer = LandingPageLinkSerializer(link)
        data = serializer.data

        self.assertEqual("", data["icon"])
        self.assertEqual("Kik Intranet", data["label"])
        self.assertEqual("#", data["href"])
