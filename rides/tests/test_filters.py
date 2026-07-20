from django.test import TestCase
from django.utils import timezone

from core.models import User
from rides.filters import RideFilter
from rides.models import Ride


class RideFilterTests(TestCase):
    def setUp(self):
        self.rider_a = User.objects.create_user(
            username="rider_a", email="a@example.com", password="x"
        )
        self.rider_b = User.objects.create_user(
            username="rider_b", email="b@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="driver", email="d@example.com", password="x"
        )

        self.en_route = self._make_ride(self.rider_a, Ride.Status.EN_ROUTE)
        self.dropoff = self._make_ride(self.rider_b, Ride.Status.DROPOFF)

    def _make_ride(self, rider, status):
        return Ride.objects.create(
            status=status,
            rider=rider,
            driver=self.driver,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=timezone.now(),
        )

    def test_filters_by_status(self):
        result = RideFilter(
            {"status": Ride.Status.EN_ROUTE}, queryset=Ride.objects.all()
        ).qs
        self.assertEqual(list(result), [self.en_route])

    def test_filters_by_rider_email_case_insensitive(self):
        result = RideFilter(
            {"rider_email": "A@EXAMPLE.COM"}, queryset=Ride.objects.all()
        ).qs
        self.assertEqual(list(result), [self.en_route])

    def test_no_filters_returns_all(self):
        result = RideFilter({}, queryset=Ride.objects.all()).qs
        self.assertEqual(result.count(), 2)
