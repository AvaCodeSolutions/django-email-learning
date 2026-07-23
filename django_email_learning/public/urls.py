from django.urls import path

from django_email_learning.public.embed_script import EmbedScriptView
from django_email_learning.public.newsletter_views import (
    NewsletterConfirmSubscriptionView,
    NewsletterUnsubscribeView,
)
from django_email_learning.public.views import CourseView, OrganizationView

app_name = "django_email_learning"

urlpatterns = [
    path(
        "organizations/<int:organization_id>/",
        OrganizationView.as_view(),
        name="organization_view",
    ),
    path(
        "organizations/<int:organization_id>/courses/<slug:course_slug>/",
        CourseView.as_view(),
        name="course_view",
    ),
    path(
        "newsletters/unsubscribe/<uuid:token>/",
        NewsletterUnsubscribeView.as_view(),
        name="newsletter_unsubscribe",
    ),
    path(
        "newsletters/confirm/<uuid:token>/",
        NewsletterConfirmSubscriptionView.as_view(),
        name="newsletter_confirm_subscription",
    ),
    path(
        "embed/del-enroll-form.js",
        EmbedScriptView.as_view(),
        name="embed_script",
    ),
]
