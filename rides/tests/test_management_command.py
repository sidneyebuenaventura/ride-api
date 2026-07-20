from datetime import datetime, timezone as dt_timezone
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import User
from rides.models import Ride, RideEvent


class LongTripsReportCommandTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="chris",
            email="chris@example.com",
            password="x",
            first_name="Chris",
            last_name="H",
        )

    def test_prints_no_trips_message_when_empty(self):
        out = StringIO()
        call_command("long_trips_report", stdout=out)
        self.assertIn("No trips over 1hr found.", out.getvalue())

    def test_prints_a_row_per_month_and_driver(self):
        pickup_at = datetime(2024, 1, 10, 8, 0, tzinfo=dt_timezone.utc)
        ride = Ride.objects.create(
            status=Ride.Status.DROPOFF,
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=pickup_at,
        )
        pickup_event = RideEvent.objects.create(
            ride=ride, description="Status changed to pickup"
        )
        RideEvent.objects.filter(pk=pickup_event.pk).update(created_at=pickup_at)
        dropoff_event = RideEvent.objects.create(
            ride=ride, description="Status changed to dropoff"
        )
        RideEvent.objects.filter(pk=dropoff_event.pk).update(
            created_at=pickup_at.replace(hour=10)
        )

        out = StringIO()
        call_command("long_trips_report", stdout=out)
        output = out.getvalue()
        self.assertIn("2024-01", output)
        self.assertIn("Chris H", output)
        self.assertIn("1", output)
