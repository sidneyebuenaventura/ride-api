from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from rides.distance import annotate_distance
from rides.filters import RideFilter
from rides.models import Ride, RideEvent
from rides.serializers import (
    RideDetailSerializer,
    RideEventSerializer,
    RideListSerializer,
)


class RideViewSet(viewsets.ModelViewSet):
    filterset_class = RideFilter

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RideDetailSerializer
        return RideListSerializer


    def get_queryset(self):
        queryset = Ride.objects.select_related("rider", "driver")

        if self.action == "retrieve":
            return queryset.prefetch_related("events")

        cutoff = timezone.now() - timedelta(hours=24)
        queryset = queryset.prefetch_related(
            Prefetch(
                "events",
                queryset=RideEvent.objects.filter(created_at__gte=cutoff).order_by(
                    "-created_at"
                ),
                to_attr="todays_ride_events",
            )
        )

        if self.action != "list":
            return queryset

        sort = self.request.query_params.get("sort", "pickup_time")
        if sort == "distance":
            lat = self.request.query_params.get("pickup_lat")
            lng = self.request.query_params.get("pickup_lng")
            if lat is None or lng is None:
                raise ValidationError(
                    "pickup_lat and pickup_lng are required when sort=distance"
                )
            radius_km = self.request.query_params.get("radius_km")
            try:
                queryset = annotate_distance(
                    queryset,
                    float(lat),
                    float(lng),
                    float(radius_km) if radius_km else None,
                )
            except ValueError as exc:
                raise ValidationError(
                    "pickup_lat, pickup_lng and radius_km must be numbers"
                ) from exc
            queryset = queryset.order_by("distance", "id")
        elif sort == "pickup_time":
            queryset = queryset.order_by("-pickup_time", "id")
        else:
            raise ValidationError("sort must be 'pickup_time' or 'distance'")

        return queryset


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related("ride").all()
    serializer_class = RideEventSerializer
