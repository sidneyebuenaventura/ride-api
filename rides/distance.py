"""DB-side distance calc so sorting by distance never pulls rows into Python.

Uses the spherical law of cosines (cheap trig, good enough at city/metro
scale) rather than PostGIS - full geospatial indexing felt like overkill for
this project's scope. A lat/lng bounding box can be applied first so the
trig itself only runs over a pre-narrowed candidate set; a plain btree index
on (pickup_latitude, pickup_longitude) can serve that range filter, even
though the trig expression itself can't use it.
"""

import math

from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import ACos, Cos, Greatest, Least, Radians, Sin

EARTH_RADIUS_KM = 6371.0


def annotate_distance(queryset, lat, lng, radius_km=None):
    """Annotate each row with `distance` (km) from (lat, lng), DB-side.

    Safe to chain into `.order_by('distance', ...)`, `.filter()`, and
    pagination slicing - it's a plain SQL expression, not a Python step.
    """
    if radius_km is not None:
        queryset = _bounding_box_filter(queryset, lat, lng, radius_km)

    lat_rad = Radians(Value(lat, output_field=FloatField()))
    lng_rad = Radians(Value(lng, output_field=FloatField()))
    row_lat_rad = Radians(F("pickup_latitude"))
    row_lng_rad = Radians(F("pickup_longitude"))

    cos_angle = Cos(lat_rad) * Cos(row_lat_rad) * Cos(row_lng_rad - lng_rad) + Sin(
        lat_rad
    ) * Sin(row_lat_rad)
    # Floating point rounding can push cos_angle a hair past +/-1 for
    # identical/near-identical points, which makes ACOS raise a domain
    # error in Postgres. Clamp it into range first.
    clamped = Least(
        Value(1.0, output_field=FloatField()),
        Greatest(Value(-1.0, output_field=FloatField()), cos_angle),
    )

    distance_expr = ExpressionWrapper(
        EARTH_RADIUS_KM * ACos(clamped), output_field=FloatField()
    )
    return queryset.annotate(distance=distance_expr)


def _bounding_box_filter(queryset, lat, lng, radius_km):
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * math.cos(math.radians(lat)) or 1e-6)
    return queryset.filter(
        pickup_latitude__range=(lat - lat_delta, lat + lat_delta),
        pickup_longitude__range=(lng - lng_delta, lng + lng_delta),
    )
