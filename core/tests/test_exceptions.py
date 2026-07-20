from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from rides.models import Ride


class ProtectedDeleteTests(TestCase):
    """on_delete=PROTECT on Ride.rider/Ride.driver means deleting a User
    still referenced by a Ride would otherwise crash with a raw
    ProtectedError (500) - core.exceptions.custom_exception_handler turns
    that into a clean 409 instead."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="x",
            role=User.Role.ADMIN,
        )
        self.rider = User.objects.create_user(
            username="rider", email="rider@example.com", password="x"
        )
        self.driver = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            password="x",
            role=User.Role.DRIVER,
        )
        Ride.objects.create(
            status=Ride.Status.EN_ROUTE,
            rider=self.rider,
            driver=self.driver,
            pickup_latitude=0,
            pickup_longitude=0,
            dropoff_latitude=0,
            dropoff_longitude=0,
            pickup_time=timezone.now(),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_deleting_a_referenced_rider_returns_a_clean_conflict(self):
        response = self.client.delete(reverse("user-detail", args=[self.rider.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("detail", response.data)
        self.assertTrue(User.objects.filter(pk=self.rider.pk).exists())

    def test_deleting_a_referenced_driver_returns_a_clean_conflict(self):
        response = self.client.delete(reverse("user-detail", args=[self.driver.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(User.objects.filter(pk=self.driver.pk).exists())

    def test_deleting_an_unreferenced_user_still_works(self):
        spare = User.objects.create_user(
            username="spare", email="spare@example.com", password="x"
        )
        response = self.client.delete(reverse("user-detail", args=[spare.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=spare.pk).exists())
