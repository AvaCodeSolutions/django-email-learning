from django.urls import path

from django_email_learning.organization_api.views import EnrollmentsView, GateUnlockView, OpenApiSchemaView, PingView

app_name = "django_email_learning"

urlpatterns = [
    path("enrollments/", EnrollmentsView.as_view(), name="enrollments"),
    path("enrollments/<int:enrollment_id>/unlock/", GateUnlockView.as_view(), name="enrollment_unlock"),
    path("ping/", PingView.as_view(), name="ping"),
    path("openapi.json", OpenApiSchemaView.as_view(), name="openapi_schema"),
]
