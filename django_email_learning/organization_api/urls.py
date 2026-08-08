from django.urls import path

from django_email_learning.organization_api.views import EnrollmentsView, OpenApiSchemaView, PingView

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollmentsView.as_view(), name="enrollments"),
    path("ping/", PingView.as_view(), name="ping"),
    path("openapi.json", OpenApiSchemaView.as_view(), name="openapi_schema"),
]
