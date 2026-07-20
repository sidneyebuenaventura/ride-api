from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import PublicTokenObtainPairView, PublicTokenRefreshView, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", PublicTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", PublicTokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(router.urls)),
]
