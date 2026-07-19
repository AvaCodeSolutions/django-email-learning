from django.urls import path

from django_email_learning.public.api.views import (
    EmbeddableEnrollView,
    EmbeddableNewsletterSubscribeView,
    EnrollView,
    NewsletterSubscribeView,
)

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollView.as_view(), name="enroll"),
    path(
        "organizations/<int:organization_id>/newsletters/subscribe/",
        NewsletterSubscribeView.as_view(),
        name="newsletter_subscribe",
    ),
    path("embed/enrollments/", EmbeddableEnrollView.as_view(), name="embed_enroll"),
    path(
        "embed/organizations/<int:organization_id>/newsletters/subscribe/",
        EmbeddableNewsletterSubscribeView.as_view(),
        name="embed_newsletter_subscribe",
    ),
]
