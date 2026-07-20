from django.test import TestCase

from core.models import User
from core.serializers import UserBriefSerializer, UserSerializer


class UserBriefSerializerTests(TestCase):
    def test_exposes_only_trimmed_fields(self):
        user = User.objects.create_user(
            username="rider", email="rider@example.com", password="x", first_name="Rae"
        )
        data = UserBriefSerializer(user).data
        self.assertEqual(
            set(data.keys()),
            {"id", "first_name", "last_name", "email", "phone_number", "role"},
        )
        self.assertNotIn("username", data)


class UserSerializerTests(TestCase):
    def test_create_hashes_password(self):
        serializer = UserSerializer(
            data={
                "username": "newdriver",
                "password": "supersecret",
                "email": "newdriver@example.com",
                "role": User.Role.DRIVER,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertNotEqual(user.password, "supersecret")
        self.assertTrue(user.check_password("supersecret"))

    def test_update_without_password_keeps_existing_password(self):
        user = User.objects.create_user(
            username="rider", email="rider@example.com", password="original"
        )
        serializer = UserSerializer(user, data={"first_name": "Updated"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.first_name, "Updated")
        self.assertTrue(updated.check_password("original"))
