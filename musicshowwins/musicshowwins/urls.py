from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from main.apps import MainConfig
from restapi.apps import RestapiConfig

main_app = MainConfig.name
restapi_app = RestapiConfig.name

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(f"{main_app}.urls")),
    path("api/", include(f"{restapi_app}.urls")),
]
