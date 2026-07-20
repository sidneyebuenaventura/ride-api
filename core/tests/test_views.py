from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.models import User


class TokenAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="rider1",
            email="rider1@example.com",
            password="secret123",
            role=User.Role.RIDER,
        )

    def test_login_works_regardless_of_role(self):
        """Obtaining a token can't itself require the admin role - that
        would make it impossible for anyone to ever log in."""
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "rider1", "password": "secret123"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_token_from_non_admin_is_rejected_on_protected_endpoint(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "rider1", "password": "secret123"},
        )
        access = response.data["access"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        protected = client.get(reverse("user-list"))
        self.assertEqual(protected.status_code, status.HTTP_403_FORBIDDEN)


class UserViewSetTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="x",
            role=User.Role.ADMIN,
        )

    def test_admin_can_list_users(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_is_rejected(self):
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
