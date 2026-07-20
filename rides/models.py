from django.conf import settings
from django.db import models


class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = "en-route", "En route"
        PICKUP = "pickup", "Pickup"
        DROPOFF = "dropoff", "Dropoff"

    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides_as_rider",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides_as_driver",
        null=True,
        blank=True,
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["pickup_latitude", "pickup_longitude"]),
        ]
        ordering = ["-pickup_time"]

    def __str__(self):
        return f"Ride #{self.pk} ({self.status})"


class RideEvent(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="events")
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["ride", "created_at"]),
            models.Index(fields=["description", "ride", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.description} (ride #{self.ride_id})"
