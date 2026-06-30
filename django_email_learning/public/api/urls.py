from django.urls import path

from django_email_learning.public.api.views import EnrollView, NewsletterSubscribeView

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollView.as_view(), name="enroll"),
    path(
        "organizations/<int:organization_id>/newsletters/subscribe/",
        NewsletterSubscribeView.as_view(),
        name="newsletter_subscribe",
    ),
]
