from django.contrib import admin
from django.urls import include, path

from .views import health

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("", include("main.urls")),
    path("api/", include("restapi.urls")),
]
