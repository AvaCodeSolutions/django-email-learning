import json
import posixpath
from datetime import datetime
from enum import StrEnum
from django.views import View
from django.utils.decorators import method_decorator
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from urllib.parse import urlparse
from pydantic import ValidationError
from django_email_learning.platform.api import serializers
from django_email_learning.models import (
    ApiKey,
    JobExecution,
    JobName,
    OrganizationUser,
)
from django_email_learning.decorators import (
    is_an_organization_member,
    is_platform_admin,
    accessible_for,
)

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})

DEFAULT_SUCCESS_THRESHOLD_MINUTES = 15
DEFAULT_WARNING_THRESHOLD_MINUTES = 45


class JobHealthStatus(StrEnum):
    SUCCESS = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@method_decorator(is_platform_admin(), name="post")
@method_decorator(is_platform_admin(), name="get")
class ApiKeyView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            key = ApiKey.generate_key()
            api_key = ApiKey(key=key, created_by=request.user)
            api_key.save()
            return JsonResponse(
                serializers.ApiKeyResponse.from_django_model(api_key).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        api_keys = ApiKey.objects.all()  # type: ignore[attr-defined]
        response_list = []
        for api_key in api_keys:
            response_list.append(
                serializers.ApiKeyResponse.from_django_model(api_key).model_dump()
            )
        return JsonResponse({"api_keys": response_list}, status=200)


@method_decorator(is_platform_admin(), name="delete")
class SingleApiKeyView(View):
    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            api_key = ApiKey.objects.get(id=kwargs["api_key_id"])
            api_key.delete()
            return JsonResponse({"message": "API Key deleted successfully"}, status=200)
        except ApiKey.DoesNotExist:
            return JsonResponse({"error": "API Key not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(is_an_organization_member(), name="get")
class JobsStatus(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        jobs_status = {}
        for job in JobName:
            last_execution = (
                JobExecution.objects.filter(job_name=job.value)
                .order_by("-started_at")
                .first()
            )
            jobs_status[job.value] = {
                "job_name": job.value,
                "last_execution_status": last_execution.status
                if last_execution
                else None,
                "last_execution_started_at": last_execution.started_at.isoformat()
                if last_execution
                else None,
                "last_execution_finished_at": last_execution.finished_at.isoformat()
                if last_execution and last_execution.finished_at
                else None,
                "job_health_status": self.calculate_job_health_status(
                    last_execution.started_at
                )
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
            warning_threshold = (
                success_threshold + 30
            )  # Ensure warning threshold is greater than success threshold
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
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor"}), name="delete"
)
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
            normalized_media_url = (
                media_url if media_url.endswith("/") else f"{media_url}/"
            )
            if parsed_url_path.startswith(normalized_media_url):
                file_path = parsed_url_path[len(normalized_media_url) :]

        if not file_path:
            return JsonResponse({"error": "file_path is required"}, status=400)

        normalized_file_path = posixpath.normpath(str(file_path)).lstrip("/")
        path_parts = normalized_file_path.split("/")
        organization_id = str(kwargs["organization_id"])

        if (
            len(path_parts) < 4
            or path_parts[0] != "uploads"
            or path_parts[2] != organization_id
            or ".." in path_parts
        ):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if not default_storage.exists(normalized_file_path):
            return JsonResponse({"error": "File not found"}, status=404)

        default_storage.delete(normalized_file_path)
        return JsonResponse({"message": "File deleted successfully"}, status=200)


@method_decorator(is_an_organization_member(), name="post")
class UpdateSessionView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateSessionRequest.model_validate(payload)
            organization_id = serializer.active_organization_id
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        if (
            not OrganizationUser.objects.filter(
                user_id=request.user.id, organization_id=organization_id
            ).exists()
            and not request.user.is_superuser
        ):
            return JsonResponse(
                {"error": "Not a valid organization for the user."}, status=409
            )
        request.session["active_organization_id"] = organization_id
        response_serializer = serializers.SessionInfo.populate_from_session(
            request.session
        )
        return JsonResponse(response_serializer.model_dump(), status=200)
