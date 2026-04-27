from django.urls import path

from .views import RedirectView, SessionsView

app_name = "oauth_integrations"

urlpatterns = [
    path("sessions/", SessionsView.as_view(), name="sessions_view"),
    path("redirect/", RedirectView.as_view(), name="redirect_view"),
]
