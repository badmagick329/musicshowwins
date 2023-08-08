from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from main.apps import MainConfig

app_name = MainConfig.name

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(f"{app_name}.urls")),
]
