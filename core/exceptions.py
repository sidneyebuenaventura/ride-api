from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """DRF's default handler doesn't know about Django's on_delete=PROTECT -
    without this, deleting a User still referenced by a Ride (rider/driver)
    crashes with a raw 500 instead of a clean error."""
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, ProtectedError):
        return Response(
            {
                "detail": "Cannot delete this object - it's still referenced by other records."
            },
            status=status.HTTP_409_CONFLICT,
        )

    return None
