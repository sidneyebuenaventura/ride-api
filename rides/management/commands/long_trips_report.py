from django.core.management.base import BaseCommand

from rides.reports import long_trips_by_month_and_driver


class Command(BaseCommand):
    help = "Print the count of trips over 1hr pickup-to-dropoff, grouped by month and driver."

    def handle(self, *args, **options):
        rows = long_trips_by_month_and_driver()
        if not rows:
            self.stdout.write("No trips over 1hr found.")
            return

        self.stdout.write(f"{'Month':<12}{'Driver':<20}{'Count of Trips > 1 hr'}")
        for row in rows:
            month = row["month"].strftime("%Y-%m")
            self.stdout.write(f"{month:<12}{row['driver_name']:<20}{row['trip_count']}")
