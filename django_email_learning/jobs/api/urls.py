from django.urls import path
from django_email_learning.jobs.api.views import DeliverContentsJobView

app_name = "django_email_learning"

urlpatterns = [
    path(
        "deliver_contents/", DeliverContentsJobView.as_view(), name="deliver_contents"
    ),
]
