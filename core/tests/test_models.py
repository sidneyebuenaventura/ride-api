from django.test import TestCase

from core.models import User


class UserModelTests(TestCase):
    def test_default_role_is_rider(self):
        user = User.objects.create_user(
            username="alice", email="alice@example.com", password="x"
        )
        self.assertEqual(user.role, User.Role.RIDER)

    def test_str_includes_role(self):
        user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="x",
            first_name="Bob",
            last_name="Jones",
            role=User.Role.ADMIN,
        )
        self.assertEqual(str(user), "Bob Jones (admin)")

    def test_str_falls_back_to_username_without_name(self):
        user = User.objects.create_user(
            username="carl", email="carl@example.com", password="x"
        )
        self.assertEqual(str(user), "carl (rider)")
