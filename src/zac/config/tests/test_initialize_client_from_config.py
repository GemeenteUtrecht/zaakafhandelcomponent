"""
Test that zds-clients can be initialized from the models holding the config.
"""
from django.test import SimpleTestCase

from .factories import ServiceFactory


class ClientTests(SimpleTestCase):

    def test_get_client_instance(self):
        service = ServiceFactory.build(api_root='https://ref.tst.vng.cloud/zrc/api/v1/')

        client = service.build_client()

        self.assertEqual(client.base_url, 'https://ref.tst.vng.cloud/zrc/api/v1/')
        self.assertIsNotNone(client.auth)

    def test_can_set_claims(self):
        service = ServiceFactory.build(api_root='https://ref.tst.vng.cloud/zrc/api/v1/')

        client = service.build_client()

        old_creds = client.auth.credentials()
        try:
            client.auth.set_claims(foo='bar')
        except Exception:
            self.fail("It should be possible to modify the claims")

        # compare credentials, the JWT should have changed
        self.assertNotEqual(client.auth.credentials(), old_creds)
