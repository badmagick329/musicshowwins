from django.urls import path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from restapi import views

schema_view = get_schema_view(
    openapi.Info(
        title="Music Show Wins API",
        default_version="v1",
        description="Get data about kpop music show wins",
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("songs", views.SongsList.as_view(), name="songs"),
]
