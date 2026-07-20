from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Only users with role='admin' may call the API.

    Checks request.user.role (a fresh DB read on every request via
    simplejwt's get_user()), not request.auth's token payload - a user
    demoted after a token was issued should lose access immediately,
    not wait for the token to expire.
    """

    message = "This endpoint requires an admin role."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == user.Role.ADMIN)
