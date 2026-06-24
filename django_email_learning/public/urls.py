from django.urls import path
from django_email_learning.public.newsletter_views import NewsletterUnsubscribeView
from django_email_learning.public.views import OrganizationView, CourseView

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
]
