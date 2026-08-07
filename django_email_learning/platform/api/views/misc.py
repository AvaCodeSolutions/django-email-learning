import json
import logging
import posixpath
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.storage import default_storage
from django.db.utils import IntegrityError
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import (
    accessible_for,
    is_an_organization_member,
    is_platform_admin,
)
from django_email_learning.error_responses import log_and_conflict_response
from django_email_learning.models import (
    ApiKey,
    ApiKeyType,
    JobExecution,
    JobName,
    Organization,
    OrganizationUser,
)
from django_email_learning.platform.api import serializers

logger = logging.getLogger(__name__)

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})

DEFAULT_SUCCESS_THRESHOLD_MINUTES = 15
DEFAULT_WARNING_THRESHOLD_MINUTES = 45


class JobHealthStatus(StrEnum):
    SUCCESS = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


def _parse_json_body(request) -> dict:  # type: ignore[no-untyped-def]
    """Reads an optional JSON body, treating anything that isn't one as `{}`.

    A bodyless POST from a form-encoded client still carries a body, so the
    content type - not emptiness - is what decides whether there is JSON to
    read. Fields the caller omits then fall back to their defaults, and any
    that have none surface as ordinary validation errors.
    """
    if not request.body or not (request.content_type or "").startswith("application/json"):
        return {}
    return json.loads(request.body)


@method_decorator(is_platform_admin(), name="post")
@method_decorator(is_platform_admin(), name="get")
class ApiKeyView(View):
    """Platform-wide keys. Restricted to platform admins, since these gate
    deployment-wide operations rather than any one organization's data.
    """

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = serializers.CreatePlatformApiKeyRequest.model_validate(_parse_json_body(request))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request body"}, status=400)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        try:
            api_key, token = ApiKey.create(
                key_type=ApiKeyType.PLATFORM,
                name=payload.name,
                created_by=request.user,
                expires_at=payload.expires_at,
            )
        except DjangoValidationError as e:
            return JsonResponse({"error": e.message_dict}, status=400)
        except IntegrityError as e:
            return log_and_conflict_response(logger, e, "Creating API key")

        return JsonResponse(
            serializers.ApiKeyCreatedResponse.from_created_key(api_key, token).model_dump(mode="json"),
            status=201,
        )

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        api_keys = ApiKey.objects.filter(key_type=ApiKeyType.PLATFORM).select_related("created_by")
        return JsonResponse(
            {
                "api_keys": [
                    serializers.ApiKeyResponse.from_django_model(api_key).model_dump(mode="json")
                    for api_key in api_keys
                ]
            },
            status=200,
        )


@method_decorator(is_platform_admin(), name="delete")
class SingleApiKeyView(View):
    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            api_key = ApiKey.objects.get(id=kwargs["api_key_id"], key_type=ApiKeyType.PLATFORM)
        except ApiKey.DoesNotExist:
            return JsonResponse({"error": "API Key not found"}, status=404)

        api_key.revoke()
        return JsonResponse({"message": "API Key revoked successfully"}, status=200)


class OrganizationApiKeyPermissionMixin:
    """Provides the hooks gating organization API key management.

    Override either in a subclass to add custom logic (plan limits, feature
    flags, a stricter role rule). Returning False rejects the request with a
    403 before any database work happens. Both receive the resolved
    `Organization` rather than its id, so a check can read the organization's
    own state without a second query.
    """

    def can_create_organization_api_key(self, request: HttpRequest, organization: Organization) -> bool:
        return True

    def can_delete_organization_api_key(self, request: HttpRequest, organization: Organization) -> bool:
        return True

    def get_target_organization(self, organization_id: int) -> Organization | None:
        # Membership has already been checked by the decorator, but a superuser
        # bypasses that and could name an organization that doesn't exist.
        return Organization.objects.filter(id=organization_id).first()


@method_decorator(is_an_organization_member(only_admin=True), name="post")
@method_decorator(is_an_organization_member(only_admin=True), name="get")
class OrganizationApiKeyView(OrganizationApiKeyPermissionMixin, View):
    """Keys an organization's own admins issue for the public API.

    Admin-only within the organization: a key is a bearer credential that acts
    with the scopes it was granted, so issuing one is a privilege escalation
    for any role that couldn't already do the thing the scope permits.
    """

    def post(self, request, organization_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization = self.get_target_organization(organization_id)
        if organization is None:
            return JsonResponse({"error": "Organization not found"}, status=404)
        if not self.can_create_organization_api_key(request, organization):
            return JsonResponse({"error": "API key creation not allowed."}, status=403)

        try:
            payload = serializers.CreateOrganizationApiKeyRequest.model_validate(_parse_json_body(request))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request body"}, status=400)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        try:
            api_key, token = ApiKey.create(
                key_type=ApiKeyType.ORGANIZATION,
                name=payload.name,
                organization_id=organization_id,
                scopes=payload.scopes,
                created_by=request.user,
                expires_at=payload.expires_at,
            )
        except DjangoValidationError as e:
            return JsonResponse({"error": e.message_dict}, status=400)
        except IntegrityError as e:
            return log_and_conflict_response(logger, e, "Creating organization API key")

        logger.info(
            "Organization API key %s created for organization %s by user %s",
            api_key.key_id,
            organization_id,
            request.user.id,
        )
        return JsonResponse(
            serializers.ApiKeyCreatedResponse.from_created_key(api_key, token).model_dump(mode="json"),
            status=201,
        )

    def get(self, request, organization_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        api_keys = ApiKey.objects.filter(
            key_type=ApiKeyType.ORGANIZATION, organization_id=organization_id
        ).select_related("created_by")
        return JsonResponse(
            {
                "api_keys": [
                    serializers.ApiKeyResponse.from_django_model(api_key).model_dump(mode="json")
                    for api_key in api_keys
                ]
            },
            status=200,
        )


@method_decorator(is_an_organization_member(only_admin=True), name="delete")
class SingleOrganizationApiKeyView(OrganizationApiKeyPermissionMixin, View):
    def delete(self, request, organization_id: int, api_key_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization = self.get_target_organization(organization_id)
        if organization is None:
            return JsonResponse({"error": "Organization not found"}, status=404)
        # Checked before the key is looked up, so a caller who may not revoke
        # can't use the 404/200 difference to probe which key ids exist.
        if not self.can_delete_organization_api_key(request, organization):
            return JsonResponse({"error": "API key deletion not allowed."}, status=403)

        # Filtering on organization_id as well as the key id keeps one
        # organization's admin from revoking another's key by guessing an id.
        try:
            api_key = ApiKey.objects.get(
                id=api_key_id,
                organization_id=organization_id,
                key_type=ApiKeyType.ORGANIZATION,
            )
        except ApiKey.DoesNotExist:
            return JsonResponse({"error": "API Key not found"}, status=404)

        api_key.revoke()
        logger.info(
            "Organization API key %s revoked for organization %s by user %s",
            api_key.key_id,
            organization_id,
            request.user.id,
        )
        return JsonResponse({"message": "API Key revoked successfully"}, status=200)


# Job health is deployment-wide operational state, not organization data, so
# it's restricted to platform admins rather than any organization member.
@method_decorator(is_platform_admin(), name="get")
class JobsStatus(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        jobs_status = {}
        for job in JobName:
            last_execution = JobExecution.objects.filter(job_name=job.value).order_by("-started_at").first()
            jobs_status[job.value] = {
                "job_name": job.value,
                "last_execution_status": last_execution.status if last_execution else None,
                "last_execution_started_at": last_execution.started_at.isoformat() if last_execution else None,
                "last_execution_finished_at": last_execution.finished_at.isoformat()
                if last_execution and last_execution.finished_at
                else None,
                "job_health_status": self.calculate_job_health_status(last_execution.started_at)
                if last_execution
                else JobHealthStatus.CRITICAL.value,
            }

        return JsonResponse({"jobs": jobs_status}, status=200)

    @staticmethod
    def calculate_job_health_status(last_execution_started_at: datetime) -> str:
        success_threshold = DJANGO_EMAIL_LEARNING_SETTINGS.get(
            "JOB_HEALTH_SUCCESS_THRESHOLD_MINUTES", DEFAULT_SUCCESS_THRESHOLD_MINUTES
        )
        warning_threshold = DJANGO_EMAIL_LEARNING_SETTINGS.get(
            "JOB_HEALTH_WARNING_THRESHOLD_MINUTES", DEFAULT_WARNING_THRESHOLD_MINUTES
        )
        if not isinstance(success_threshold, int) or success_threshold <= 0:
            success_threshold = DEFAULT_SUCCESS_THRESHOLD_MINUTES
        if not isinstance(warning_threshold, int) or warning_threshold <= 0:
            warning_threshold = DEFAULT_WARNING_THRESHOLD_MINUTES
        if warning_threshold <= success_threshold:
            warning_threshold = success_threshold + 30  # Ensure warning threshold is greater than success threshold
        now = timezone.now()
        time_diff = now - last_execution_started_at
        minutes_diff = time_diff.total_seconds() / 60
        if minutes_diff <= success_threshold:
            return JobHealthStatus.SUCCESS.value
        elif minutes_diff <= warning_threshold:
            return JobHealthStatus.WARNING.value
        else:
            return JobHealthStatus.CRITICAL.value


class RootView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return JsonResponse({"message": "Email Learning API is running."}, status=200)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="delete")
class FileView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # check file extension
        allowed_extensions = ["png", "jpg", "jpeg", "svg"]
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension not in allowed_extensions:
            return JsonResponse({"error": "Invalid file type"}, status=400)

        date_prefix = timezone.now().strftime("%Y%m%d")

        file_path = default_storage.save(
            f"uploads/{date_prefix}/{kwargs['organization_id']}/{uploaded_file.name}",
            uploaded_file,
        )
        file_url = default_storage.url(file_path)
        return JsonResponse({"file_url": file_url, "file_path": file_path}, status=201)

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request body"}, status=400)

        file_path = payload.get("file_path")
        file_url = payload.get("file_url")

        if not file_path and file_url:
            parsed_url_path = urlparse(file_url).path
            media_url = settings.MEDIA_URL or "/media/"
            normalized_media_url = media_url if media_url.endswith("/") else f"{media_url}/"
            if parsed_url_path.startswith(normalized_media_url):
                file_path = parsed_url_path[len(normalized_media_url) :]

        if not file_path:
            return JsonResponse({"error": "file_path is required"}, status=400)

        normalized_file_path = posixpath.normpath(str(file_path)).lstrip("/")
        path_parts = normalized_file_path.split("/")
        organization_id = str(kwargs["organization_id"])

        if len(path_parts) < 4 or path_parts[0] != "uploads" or path_parts[2] != organization_id or ".." in path_parts:
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if not default_storage.exists(normalized_file_path):
            return JsonResponse({"error": "File not found"}, status=404)

        default_storage.delete(normalized_file_path)
        return JsonResponse({"message": "File deleted successfully"}, status=200)


@method_decorator(is_an_organization_member(allow_active_org_fallback=True), name="post")
class UpdateSessionView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateSessionRequest.model_validate(payload)
            organization_id = serializer.active_organization_id
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        if (
            not OrganizationUser.objects.filter(user_id=request.user.id, organization_id=organization_id).exists()
            and not request.user.is_superuser
        ):
            return JsonResponse({"error": "Not a valid organization for the user."}, status=409)
        request.session["active_organization_id"] = organization_id
        response_serializer = serializers.SessionInfo.populate_from_session(request.session)
        return JsonResponse(response_serializer.model_dump(), status=200)
