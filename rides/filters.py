import django_filters as filters

from rides.models import Ride


class RideFilter(filters.FilterSet):
    status = filters.ChoiceFilter(field_name="status", choices=Ride.Status.choices)
    rider_email = filters.CharFilter(field_name="rider__email", lookup_expr="iexact")

    class Meta:
        model = Ride
        fields = ["status", "rider_email"]
