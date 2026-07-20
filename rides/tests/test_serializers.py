from datetime import timedelta

from django.db.models import Prefetch
from django.test import TestCase
from django.utils import timezone

from core.models import User
from rides.models import Ride, RideEvent
from rides.serializers import (
    RideDetailSerializer,
    RideEventSerializer,
    RideListSerializer,
    RideWriteSerializer,
)


class RideSerializerTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x", first_name="Rae"
        )
        self.driver = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            password="x",
            first_name="Dan",
        )
        self.ride = Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=1.0,
            pickup_longitude=2.0,
            dropoff_latitude=3.0,
            dropoff_longitude=4.0,
            pickup_time=timezone.now(),
        )
        self.recent_event = RideEvent.objects.create(
            ride=self.ride, description="Status changed to pickup"
        )
        old_event = RideEvent.objects.create(
            ride=self.ride, description="Status changed to dropoff"
        )
        RideEvent.objects.filter(pk=old_event.pk).update(
            created_at=timezone.now() - timedelta(hours=48)
        )

    def test_list_serializer_exposes_rider_driver_ids_and_nested_users(self):
        ride = Ride.objects.select_related("rider", "driver").get(pk=self.ride.pk)
        ride.todays_ride_events = []  # normally set by the Prefetch(to_attr=...) in the view
        data = RideListSerializer(ride).data
        self.assertEqual(data["id_rider"], self.rider.pk)
        self.assertEqual(data["id_driver"], self.driver.pk)
        self.assertEqual(data["rider"]["email"], "rider@example.com")
        self.assertEqual(data["driver"]["email"], "driver@example.com")

    def test_list_serializer_only_shows_events_from_the_prefetched_to_attr(self):
        cutoff = timezone.now() - timedelta(hours=24)
        ride = Ride.objects.prefetch_related(
            Prefetch(
                "events",
                queryset=RideEvent.objects.filter(created_at__gte=cutoff),
                to_attr="todays_ride_events",
            )
        ).get(pk=self.ride.pk)

        data = RideListSerializer(ride).data
        event_ids = [e["id"] for e in data["todays_ride_events"]]
        self.assertEqual(event_ids, [self.recent_event.pk])
        self.assertNotIn("ride_events", data)

    def test_detail_serializer_includes_full_event_history(self):
        ride = Ride.objects.prefetch_related("events").get(pk=self.ride.pk)
        ride.todays_ride_events = []
        data = RideDetailSerializer(ride).data
        self.assertEqual(len(data["ride_events"]), 2)


class RideWriteSerializerTests(TestCase):
    """RideListSerializer's rider/driver are read-only nested objects, so
    create/update needs its own serializer with plain writable FKs."""

    def setUp(self):
        self.rider = User.objects.create_user(
            username="write_rider", email="write_rider@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="write_driver", email="write_driver@example.com", password="x"
        )
        self.payload = {
            "status": Ride.Status.EN_ROUTE,
            "rider": self.rider.id,
            "driver": self.driver.id,
            "pickup_latitude": 1.0,
            "pickup_longitude": 2.0,
            "dropoff_latitude": 3.0,
            "dropoff_longitude": 4.0,
            "pickup_time": timezone.now(),
        }

    def test_creates_ride_with_rider_and_driver(self):
        serializer = RideWriteSerializer(data=self.payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        ride = serializer.save()
        self.assertEqual(ride.rider, self.rider)
        self.assertEqual(ride.driver, self.driver)

    def test_rejects_nonexistent_rider_with_a_validation_error(self):
        self.payload["rider"] = 999999
        serializer = RideWriteSerializer(data=self.payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("rider", serializer.errors)


class RideEventSerializerStandaloneTests(TestCase):
    """Unlike NestedRideEventSerializer (embedded in a Ride payload), the
    standalone serializer needs a writable `ride` field - it isn't implied
    by nesting when hit directly via /api/ride-events/."""

    def test_ride_field_is_writable(self):
        rider = User.objects.create_user(
            username="event_rider", email="event_rider@example.com", password="x"
        )
        driver = User.objects.create_user(
            username="event_driver", email="event_driver@example.com", password="x"
        )
        ride = Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=rider,
            driver=driver,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=timezone.now(),
        )
        serializer = RideEventSerializer(
            data={"ride": ride.id, "description": "Status changed to pickup"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        event = serializer.save()
        self.assertEqual(event.ride, ride)
