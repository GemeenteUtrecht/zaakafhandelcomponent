import json

from django.urls import reverse

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import SuperUserFactory
from zac.landing.tests.factories import (
    LandingPageConfigurationFactory,
    LandingPageLinkFactory,
    LandingPageSectionFactory,
)


class LandingPageConfigurationViewTestCase(APITestCase):
    endpoint = reverse("landing-page-configuration")

    def setUp(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

    def test_get_solo(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual("Startpagina Werkomgeving", data["title"])
        self.assertEqual(None, data["image"])
        self.assertEqual([], data["sections"])
        self.assertEqual([], data["links"])

    def test_factory(self):
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

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual("Startpagina Werkomgeving", data["title"])
        self.assertIn("http://testserver/media/example", data["image"])
        self.assertEqual("Processen en activiteiten", data["sections"][0]["name"])
        self.assertEqual("account_tree", data["sections"][0]["icon"])
        self.assertEqual("post_add", data["sections"][0]["links"][0]["icon"])
        self.assertEqual(
            "Nieuwe taak starten", data["sections"][0]["links"][0]["label"]
        )
        self.assertEqual("/zaak-starten", data["sections"][0]["links"][0]["href"])
        self.assertEqual("Kik Intranet", data["links"][0]["label"])
        self.assertEqual("http://www.example.com", data["links"][0]["href"])
