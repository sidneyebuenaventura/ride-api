from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.models import User
from core.serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer


class PublicTokenObtainPairView(TokenObtainPairView):
    """Logging in obviously can't require the IsAdminRole permission
    that's the DRF-wide default - nobody would ever get a token."""

    permission_classes = [AllowAny]


class PublicTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
