from django.urls import path

from .views import EditTextView

app_name = "django_email_learning"

urlpatterns = [
    path(
        "organizations/<int:organization_id>/edit-text/",
        EditTextView.as_view(),
        name="edit_text",
    ),
]
