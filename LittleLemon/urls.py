"""URL configuration for the LittleLemon project."""

from django.contrib import admin
from django.urls import include, path
from djoser.views import UserViewSet

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("LittleLemonAPI.urls")),
    # Djoser: /api/users/ (register), /api/users/me/, /api/token/login/, /api/token/logout/
    path("api/", include("djoser.urls")),
    path("api/", include("djoser.urls.authtoken")),
    # Alias required by the project brief: /api/users/users/me/
    path(
        "api/users/users/me/",
        UserViewSet.as_view({"get": "me", "put": "me", "patch": "me", "delete": "me"}),
        name="user-me-alias",
    ),
]
