from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Riders, drivers and admins are all just Users with a role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        RIDER = "rider", "Rider"
        DRIVER = "driver", "Driver"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10, choices=Role.choices, default=Role.RIDER, db_index=True
    )
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
