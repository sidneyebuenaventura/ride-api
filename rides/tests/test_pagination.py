from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import User
from rides.models import Ride
from rides.pagination import RidePagination


class RidePaginationTests(TestCase):
    def test_defaults(self):
        self.assertEqual(RidePagination.page_size, 20)
        self.assertEqual(RidePagination.page_size_query_param, "page_size")
        self.assertEqual(RidePagination.max_page_size, 100)

    def test_page_size_query_param_is_honored_and_capped(self):
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="x",
            role=User.Role.ADMIN,
        )
        rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        driver = User.objects.create_user(
            username="driver", email="driver@example.com", password="x"
        )
        for _ in range(5):
            Ride.objects.create(
                status=Ride.Status.EN_ROUTE,
                rider=rider,
                driver=driver,
                pickup_latitude=0,
                pickup_longitude=0,
                dropoff_latitude=0,
                dropoff_longitude=0,
                pickup_time=timezone.now(),
            )

        client = APIClient()
        client.force_authenticate(admin)
        response = client.get(reverse("ride-list"), {"page_size": 2})
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)
