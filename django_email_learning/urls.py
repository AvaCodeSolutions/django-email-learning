from django.apps import apps
from django.urls import include, path

from django_email_learning.analytics import urls as analytics_urls
from django_email_learning.jobs.api import urls as jobs_api_urls
from django_email_learning.personalised import urls as personalised_urls
from django_email_learning.personalised.api import urls as personalised_api_urls
from django_email_learning.platform import urls as platform_urls
from django_email_learning.platform.api import urls as api_urls
from django_email_learning.public import urls as public_urls
from django_email_learning.public.api import urls as public_api_urls

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
    path("api/analytics/", include(analytics_urls, namespace="api_analytics")),
]

if apps.is_installed("django_email_learning.oauth_integrations"):
    urlpatterns += [
        path(
            "oauth/",
            include(
                "django_email_learning.oauth_integrations.urls",
                namespace="oauth_integrations",
            ),
        ),
    ]

if apps.is_installed("django_email_learning.ai"):
    urlpatterns += [
        path(
            "api/ai/",
            include("django_email_learning.ai.urls", namespace="api_ai"),
        ),
    ]
