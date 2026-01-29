from django.urls import path, include
from django_email_learning.platform.api import urls as api_urls
from django_email_learning.platform import urls as platform_urls
from django_email_learning.personalised.api import urls as personalised_api_urls
from django_email_learning.personalised import urls as personalised_urls
from django_email_learning.public.api import urls as public_api_urls
from django_email_learning.public import urls as public_urls
from django_email_learning.jobs.api import urls as jobs_api_urls

app_name = "django_email_learning"

urlpatterns = [
    path("api/platform/", include(api_urls, namespace="api_platform")),
    path(
        "api/personalised/",
        include(personalised_api_urls, namespace="api_personalised"),
    ),
    path("api/public/", include(public_api_urls, namespace="api_public")),
    path("platform/", include(platform_urls, namespace="platform")),
    path("public/", include(public_urls, namespace="public")),
    path("my/", include(personalised_urls, namespace="personalised")),
    path("api/jobs/", include(jobs_api_urls, namespace="api_jobs")),
]
