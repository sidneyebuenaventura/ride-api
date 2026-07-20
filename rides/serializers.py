from rest_framework import serializers

from core.serializers import UserBriefSerializer
from rides.models import Ride, RideEvent


class NestedRideEventSerializer(serializers.ModelSerializer):
    """Used when a RideEvent is embedded inside a Ride's payload - the
    parent ride is already implied by the nesting, so no need for a `ride`
    field here."""

    class Meta:
        model = RideEvent
        fields = ["id", "description", "created_at"]


class RideEventSerializer(serializers.ModelSerializer):
    """Standalone representation for /api/ride-events/ - `ride` is a normal
    writable FK here since, unlike the nested case, it isn't implied."""

    class Meta:
        model = RideEvent
        fields = ["id", "ride", "description", "created_at"]


class RideListSerializer(serializers.ModelSerializer):
    """Used for list (and as the base for RideDetailSerializer) -
    deliberately excludes full event history.

    todays_ride_events comes from a Prefetch(to_attr=...) set up in
    RideViewSet.get_queryset(), so reading it here never triggers an extra
    query per ride.
    """

    rider = UserBriefSerializer(read_only=True)
    driver = UserBriefSerializer(read_only=True)
    id_rider = serializers.IntegerField(source="rider_id", read_only=True)
    id_driver = serializers.IntegerField(
        source="driver_id", read_only=True, allow_null=True
    )
    todays_ride_events = NestedRideEventSerializer(many=True, read_only=True)
    distance = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "rider",
            "driver",
            "id_rider",
            "id_driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
            "todays_ride_events",
            "distance",
        ]


class RideDetailSerializer(RideListSerializer):
    """Used for retrieve() only - a single ride, so its full event history
    is bounded regardless of how large the RideEvent table gets overall.
    """

    ride_events = NestedRideEventSerializer(many=True, read_only=True, source="events")

    class Meta(RideListSerializer.Meta):
        fields = RideListSerializer.Meta.fields + ["ride_events"]


class RideWriteSerializer(serializers.ModelSerializer):
    """Used for create/update. rider/driver are plain writable FKs here -
    RideListSerializer's version of those fields is read-only (nested user
    objects), so it can't be used to set them."""

    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "rider",
            "driver",
            "pickup_latitude",
            "pickup_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
            "pickup_time",
        ]
