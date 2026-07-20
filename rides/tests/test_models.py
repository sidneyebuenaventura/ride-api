from django.test import TestCase
from django.utils import timezone

from core.models import User
from rides.models import Ride, RideEvent


class RideModelTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="driver", email="driver@example.com", password="x"
        )

    def make_ride(self, **overrides):
        defaults = {
            "status": Ride.Status.EN_ROUTE,
            "rider": self.rider,
            "driver": self.driver,
            "pickup_latitude": 37.7749,
            "pickup_longitude": -122.4194,
            "dropoff_latitude": 37.7849,
            "dropoff_longitude": -122.4094,
            "pickup_time": timezone.now(),
        }
        defaults.update(overrides)
        return Ride.objects.create(**defaults)

    def test_str_includes_status(self):
        ride = self.make_ride()
        self.assertIn(ride.status, str(ride))

    def test_default_ordering_is_by_pickup_time_desc(self):
        earlier = self.make_ride(
            pickup_time=timezone.now() - timezone.timedelta(hours=2)
        )
        later = self.make_ride(pickup_time=timezone.now())
        self.assertEqual(list(Ride.objects.all()), [later, earlier])

    def test_ride_event_str_includes_ride_id(self):
        ride = self.make_ride()
        event = RideEvent.objects.create(
            ride=ride, description="Status changed to pickup"
        )
        self.assertIn(str(ride.pk), str(event))

    def test_deleting_ride_cascades_to_events(self):
        ride = self.make_ride()
        RideEvent.objects.create(ride=ride, description="Status changed to pickup")
        ride.delete()
        self.assertEqual(RideEvent.objects.count(), 0)
