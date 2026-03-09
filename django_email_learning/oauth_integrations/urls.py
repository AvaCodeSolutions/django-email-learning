from django.urls import path

from .views import RedirectView, SessionView, SessionsView

app_name = "oauth_integrations"

urlpatterns = [
    path("sessions/", SessionsView.as_view(), name="sessions_view"),
    path("sessions/<str:session_id>/", SessionView.as_view(), name="session_view"),
    path("redirect/", RedirectView.as_view(), name="redirect_view"),
]
