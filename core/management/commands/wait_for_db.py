import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for the database to accept connections, retrying with a fixed delay."

    def add_arguments(self, parser):
        parser.add_argument("--max-attempts", type=int, default=10)
        parser.add_argument("--delay", type=float, default=1.0)

    def handle(self, *args, **options):
        max_attempts = options["max_attempts"]
        delay = options["delay"]

        for attempt in range(1, max_attempts + 1):
            try:
                connection.ensure_connection()
            except OperationalError:
                self.stdout.write(
                    f"database unavailable, retrying in {delay}s ({attempt}/{max_attempts})"
                )
                time.sleep(delay)
            else:
                self.stdout.write(self.style.SUCCESS("database available"))
                return

        raise SystemExit("database never became available")
