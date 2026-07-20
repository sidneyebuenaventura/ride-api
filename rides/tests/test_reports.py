from datetime import datetime, timezone as dt_timezone

from django.test import TestCase

from core.models import User
from rides.models import Ride, RideEvent
from rides.reports import long_trips_by_month_and_driver


class LongTripsReportTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        self.driver_chris = User.objects.create_user(
            username="chris",
            email="chris@example.com",
            password="x",
            first_name="Chris",
            last_name="H",
        )
        self.driver_howard = User.objects.create_user(
            username="howard",
            email="howard@example.com",
            password="x",
            first_name="Howard",
            last_name="Y",
        )

    def _ride_with_events(self, driver, pickup_at, dropoff_at):
        ride = Ride.objects.create(
            status=Ride.Status.DROPOFF,
            rider=self.rider,
            driver=driver,
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
        RideEvent.objects.filter(pk=dropoff_event.pk).update(created_at=dropoff_at)
        return ride

    def test_counts_only_trips_over_one_hour_grouped_by_month_and_driver(self):
        jan = datetime(2024, 1, 10, 8, 0, tzinfo=dt_timezone.utc)
        # Chris: one long trip (90 min) and one short trip (20 min) in January
        self._ride_with_events(self.driver_chris, jan, jan.replace(hour=9, minute=30))
        self._ride_with_events(self.driver_chris, jan, jan.replace(minute=20))
        # Howard: one long trip (2 hours) in January
        self._ride_with_events(self.driver_howard, jan, jan.replace(hour=10))
        # Chris: one long trip (75 min) in February
        feb = datetime(2024, 2, 5, 8, 0, tzinfo=dt_timezone.utc)
        self._ride_with_events(self.driver_chris, feb, feb.replace(hour=9, minute=15))

        rows = long_trips_by_month_and_driver()
        counts = {
            (r["month"].strftime("%Y-%m"), r["driver_name"]): r["trip_count"]
            for r in rows
        }

        self.assertEqual(counts[("2024-01", "Chris H")], 1)
        self.assertEqual(counts[("2024-01", "Howard Y")], 1)
        self.assertEqual(counts[("2024-02", "Chris H")], 1)

    def test_exactly_one_hour_is_not_counted(self):
        exactly_one_hour = datetime(2024, 3, 1, 8, 0, tzinfo=dt_timezone.utc)
        self._ride_with_events(
            self.driver_chris, exactly_one_hour, exactly_one_hour.replace(hour=9)
        )
        rows = long_trips_by_month_and_driver()
        self.assertEqual(rows, [])

    def test_ride_without_dropoff_event_is_excluded(self):
        pickup_only = datetime(2024, 4, 1, 8, 0, tzinfo=dt_timezone.utc)
        ride = Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=self.rider,
            driver=self.driver_chris,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=pickup_only,
        )
        pickup_event = RideEvent.objects.create(
            ride=ride, description="Status changed to pickup"
        )
        RideEvent.objects.filter(pk=pickup_event.pk).update(created_at=pickup_only)

        rows = long_trips_by_month_and_driver()
        self.assertEqual(rows, [])
