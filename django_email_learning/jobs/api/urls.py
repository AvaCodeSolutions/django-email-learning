from django.urls import path
from django_email_learning.jobs.api.views import (
    DeliverContentsJobView,
    CheckIMAPJobView,
)

app_name = "django_email_learning"

urlpatterns = [
    path(
        "deliver_contents/",
        DeliverContentsJobView.as_view(),
        name="deliver_contents",
    ),
    path(
        "check_imap_connections/",
        CheckIMAPJobView.as_view(),
        name="check_imap_connections",
    ),
]
