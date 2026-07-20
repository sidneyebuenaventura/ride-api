from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from core.models import User
from core.permissions import IsAdminRole


class IsAdminRolePermissionTests(TestCase):
    def setUp(self):
        self.permission = IsAdminRole()
        self.request = RequestFactory().get("/api/rides/")

    def test_admin_user_is_allowed(self):
        self.request.user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="x",
            role=User.Role.ADMIN,
        )
        self.assertTrue(self.permission.has_permission(self.request, None))

    def test_rider_user_is_denied(self):
        self.request.user = User.objects.create_user(
            username="rider",
            email="rider@example.com",
            password="x",
            role=User.Role.RIDER,
        )
        self.assertFalse(self.permission.has_permission(self.request, None))

    def test_driver_user_is_denied(self):
        self.request.user = User.objects.create_user(
            username="driver",
            email="driver@example.com",
            password="x",
            role=User.Role.DRIVER,
        )
        self.assertFalse(self.permission.has_permission(self.request, None))

    def test_anonymous_user_is_denied(self):
        self.request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(self.request, None))
