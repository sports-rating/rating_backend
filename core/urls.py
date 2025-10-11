from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import path, include
from django.conf.urls.static import static

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.urls")),
    path('health-check/', include('health_check.urls')),
    path("", lambda _: JsonResponse({"message": "OK"})),
]

"""
Browser enforces Basic Authentication for accessing the documentation: /docs/
"""
urlpatterns += [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[BasicAuthentication],
            permission_classes=[IsAuthenticated],
        ),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
