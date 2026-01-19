from django.core.management import BaseCommand

from ...subscriptions import subscribe_all


class Command(BaseCommand):
    help = "Set up the webhook subscriptions"

    def add_arguments(self, parser):
        parser.add_argument("domain")

    def handle(self, **options):
        subs = subscribe_all(options["domain"])
        self.stdout.write(f"Subscribed to {len(subs)} notification APIs.")
