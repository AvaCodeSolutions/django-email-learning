from django.urls import path
from django_email_learning.public.views import OrganizationView

app_name = "django_email_learning"

urlpatterns = [
    path(
        "organizations/<int:organization_id>/",
        OrganizationView.as_view(),
        name="organization_view",
    ),
]
