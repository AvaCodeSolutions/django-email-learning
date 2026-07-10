import logging
from typing import Dict

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View

from django_email_learning.decorators import (
    is_an_organization_member,
    is_platform_admin,
)
from django_email_learning.models import OrganizationUser
from django_email_learning.platform.views.base import BasePlatformView
from django_email_learning.services import jwt_service
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE


@method_decorator(login_required, name="dispatch")
@method_decorator(is_platform_admin(), name="dispatch")
class ApiKeys(BasePlatformView):
    template_name = "platform/settings_api_keys.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("API Keys")
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "settings": _("Settings"),
            "api_keys": _("API Keys"),
            "add_api_key": _("Add API Key"),
            "display_key": _("Display Key"),
            "hide_key": _("Hide Key"),
            "actions": _("Actions"),
            "key": _("Key"),
            "created_at": _("Created At"),
            "delete": _("Delete"),
            "are_you_sure_delete_key": _("Are you sure you want to delete this API key?"),
            "created_by": _("Created By"),
            "cancel": _("Cancel"),
            "confirm_deletion": _("Confirm Deletion"),
            "api_key_intro": _(
                "API keys allow external applications to interact with the platform and execute jobs."
                " This is ideal for using cloud scheduling or third-party integrations instead of managing"
                " local cron jobs. You can create, view, and manage your keys below."
            ),
        }


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class PrivateFileView(View):
    """
    A view to serve private files stored in the location defined by PRIVATE_FILE_STORAGE.
    The file path is expected to be passed as a query parameter named 'file_path'.
    """

    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        token = request.GET.get("token")

        if not token:
            return HttpResponseBadRequest("Missing 'token' query parameter.")

        try:
            decoded_token = jwt_service.decode_jwt(token)
        except (jwt_service.InvalidTokenException, jwt_service.ExpiredTokenException):
            return HttpResponseBadRequest("Invalid or expired token.")

        org_id = decoded_token.get("org_id")
        file_path = decoded_token.get("file_path")

        if not file_path or not org_id:
            logging.error("Token is missing required fields. Decoded token: %s", decoded_token)
            return HttpResponseBadRequest("Missing 'file_path' or 'org_id' in token.")

        if (
            not request.user.is_superuser
            and not OrganizationUser.objects.filter(
                user=request.user,
                organization_id=org_id,
                role__in=["admin", "editor", "instructor", "viewer"],
            ).exists()
        ):  # type: ignore[misc]
            return HttpResponseNotFound("File not found.")

        if not PRIVATE_FILE_STORAGE.exists(file_path):
            return HttpResponseNotFound("File not found.")

        file = PRIVATE_FILE_STORAGE.open(file_path)
        response = FileResponse(file)
        return response


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class Analytics(BasePlatformView):
    template_name = "platform/analytics.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Analytics")
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "analytics": _("Analytics"),
            "filters": _("Filters"),
            "course": _("Course"),
            "all_courses": _("All Courses"),
            "date_from": _("From"),
            "date_to": _("To"),
            "granularity": _("Granularity"),
            "day": _("Day"),
            "week": _("Week"),
            "month": _("Month"),
            "apply": _("Apply"),
            "enrollments_over_time": _("Enrollments Over Time"),
            "enrollment_status_breakdown": _("Enrollment Status Breakdown"),
            "completion_funnel": _("Completion Funnel"),
            "completion_funnel_tooltip": _(
                "Shows how many learners received each piece of content. The bar length is relative to the"
                " content with the most deliveries, so you can quickly see where learners drop off."
            ),
            "average_progress": _("Average Progress"),
            "time_to_complete": _("Time to Complete"),
            "email_delivery_over_time": _("Email Delivery Over Time"),
            "email_delivery_status_breakdown": _("Email Delivery Status"),
            "email_open_rate": _("Email Open Rate"),
            "downloads": _("Downloads"),
            "download_learner_progress": _("Learner Progress"),
            "download_delivery_log": _("Delivery Log"),
            "download_completion_summary": _("Completion Summary"),
            "learners_reached": _("Learners Reached"),
            "open_rate": _("Open Rate"),
            "average_days": _("Avg. Days"),
            "active": _("Active"),
            "completed": _("Completed"),
            "deactivated": _("Deactivated"),
            "no_data": _("No data available for the selected filters."),
            "loading": _("Loading…"),
        }
