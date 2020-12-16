from django.core.management import BaseCommand

import requests
from zgw_consumers.models import Service


class Command(BaseCommand):
    help = "Fetches and caches the API specs from remote services"

    def handle(self, **options):
        for service in Service.objects.all():
            client = service.build_client()
            try:
                client.schema
                self.stdout.write(f"Fetched schema for {service}")
            except requests.HTTPError as exc:
                self.stdout.write(f"Fetching schema for {service} failed with {exc}")
