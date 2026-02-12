import logging
import os

from django.core.management import BaseCommand, CommandError
from django.utils.crypto import get_random_string

import requests
from zds_client import ClientAuth
from zgw_consumers.concurrent import parallel

logger = logging.getLogger("performance")


class Command(BaseCommand):
    help = "Run some network calls to profile the infrastructure"
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--client-id",
            help="Client ID to use for the JWT. Defaults to the CLIENT_ID envvar.",
            default=os.getenv("CLIENT_ID", ""),
        )
        parser.add_argument(
            "--secret",
            help="Client secret to use for the JWT. Defaults to the CLIENT_SECRET envvar.",
            default=os.getenv("CLIENT_SECRET", ""),
        )
        parser.add_argument(
            "--concurrency",
            type=int,
            help="If provided, the number of parallel requests to make.",
        )
        parser.add_argument(
            "--endpoint",
            help="Endpoint to call",
            default="https://open-zaak.cg-intern.ont.utrecht.nl/zaken/api/v1/zaken",
        )

    def handle(self, **options):
        if not options["client_id"] or not options["secret"]:
            raise CommandError(
                "You must provide a Client ID and secret. See `run_benchmark --help` "
                "for information on how to specify these"
            )

        auth = ClientAuth(options["client_id"], options["secret"])
        headers = {**auth.credentials(), "Accept-Crs": "EPSG:4326"}

        def make_request():
            reference = get_random_string(length=5)
            logger.info("Request %s start", reference)
            response = requests.get(
                options["endpoint"], headers=headers, timeout=(10, 30)
            )
            logger.info(
                "Request %s completed, elapsed: %fs",
                reference,
                response.elapsed.total_seconds(),
            )

        concurrency = options["concurrency"]

        self.stdout.write(f"Endpoint: {options['endpoint']}")
        self.stdout.write(f"Concurrency: {concurrency or 'single-call'}")
        self.stdout.write("")

        if not concurrency:
            make_request()

        else:
            with parallel(max_workers=concurrency) as executor:
                for _ in range(concurrency):
                    executor.submit(make_request)
