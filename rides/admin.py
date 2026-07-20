from django.contrib import admin

from rides.models import Ride, RideEvent


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "rider", "driver", "pickup_time")
    list_filter = ("status",)


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ("id", "ride", "description", "created_at")
