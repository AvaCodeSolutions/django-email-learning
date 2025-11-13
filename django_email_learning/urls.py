from django.urls import path, include
from django_email_learning.api import urls as api_urls
from django_email_learning.platform import urls as platform_urls

app_name = "django_email_learning"

urlpatterns = [
    path("api/", include(api_urls, namespace="api")),
    path("platform/", include(platform_urls, namespace="platform")),
]
