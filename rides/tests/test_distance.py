from django.test import TestCase
from django.utils import timezone

from core.models import User
from rides.distance import annotate_distance
from rides.models import Ride


class AnnotateDistanceTests(TestCase):
    def setUp(self):
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="driver", email="driver@example.com", password="x"
        )
        # San Francisco
        self.near = self._make_ride(37.7749, -122.4194)
        # New York - roughly 4130km from SF
        self.far = self._make_ride(40.7128, -74.0060)

    def _make_ride(self, lat, lng):
        return Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=lat,
            pickup_longitude=lng,
            dropoff_latitude=lat,
            dropoff_longitude=lng,
            pickup_time=timezone.now(),
        )

    def test_orders_by_ascending_distance(self):
        qs = annotate_distance(Ride.objects.all(), 37.7749, -122.4194).order_by(
            "distance"
        )
        self.assertEqual(list(qs), [self.near, self.far])

    def test_distance_to_identical_point_is_near_zero(self):
        """This is exactly the case that triggers ACos domain errors if the
        cos_angle expression isn't clamped to [-1, 1] before ACos runs."""
        ride = annotate_distance(
            Ride.objects.filter(pk=self.near.pk), 37.7749, -122.4194
        ).get()
        self.assertLess(ride.distance, 0.01)

    def test_far_point_distance_is_roughly_correct(self):
        ride = annotate_distance(
            Ride.objects.filter(pk=self.far.pk), 37.7749, -122.4194
        ).get()
        self.assertGreater(ride.distance, 4000)
        self.assertLess(ride.distance, 4200)

    def test_bounding_box_excludes_far_rides(self):
        qs = annotate_distance(Ride.objects.all(), 37.7749, -122.4194, radius_km=50)
        self.assertEqual(list(qs), [self.near])
