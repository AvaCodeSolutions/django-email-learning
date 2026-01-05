from django.urls import path, include
from django_email_learning.platform.api import urls as api_urls
from django_email_learning.platform import urls as platform_urls
from django_email_learning.personalised.api import urls as personalised_api_urls
from django_email_learning.personalised import urls as personalised_urls

app_name = "django_email_learning"

urlpatterns = [
    path("api/platform/", include(api_urls, namespace="api_platform")),
    path(
        "api/personalised/",
        include(personalised_api_urls, namespace="api_personalised"),
    ),
    path("platform/", include(platform_urls, namespace="platform")),
    path("my/", include(personalised_urls, namespace="personalised")),
]
