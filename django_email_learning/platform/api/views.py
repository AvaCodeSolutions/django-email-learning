from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.utils import IntegrityError
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta, datetime
from pydantic import ValidationError
from enum import StrEnum
from django_email_learning.platform.api import serializers
from django_email_learning.platform.api.pagniated_api_mixin import PaginatedApiMixin
from django_email_learning.models import (
    ApiKey,
    Course,
    CourseContent,
    Enrollment,
    EnrollmentStatus,
    ImapConnection,
    JobExecution,
    JobName,
    Learner,
    OrganizationUser,
    Organization,
)
from django_email_learning.decorators import (
    accessible_for,
    is_an_organization_member,
    is_platform_admin,
)
from typing import Any
import json
import logging


logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class CourseView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(
                organization_id=kwargs["organization_id"]
            )
            course.save()
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        courses = Course.objects.filter(organization_id=kwargs["organization_id"])
        enabled = request.GET.get("enabled")
        if enabled is not None:
            if enabled.lower() in ["true", "yes"]:
                courses = courses.filter(enabled=True)
            elif enabled.lower() in ["false", "no"]:
                courses = courses.filter(enabled=False)

        response_list = []
        for course in courses:
            response_list.append(
                serializers.CourseResponse.model_validate(course).model_dump()
            )
        return JsonResponse({"courses": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class CourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseContentRequest.model_validate(payload)
            course = Course.objects.get(id=kwargs["course_id"])
            if serializer.priority is None:
                # Set priority to max existing priority + 1
                max_priority = (
                    CourseContent.objects.filter(course_id=course.id)
                    .aggregate(max_priority=models.Max("priority"))
                    .get("max_priority")
                )
                serializer.priority = (max_priority or 0) + 1
            course_content = serializer.to_django_model(course=course)

            return JsonResponse(
                serializers.CourseContentResponse.model_validate(
                    course_content
                ).model_dump(),
                status=201,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            course_contents = course.coursecontent_set.all().order_by("priority")
            response_list = []
            for content in course_contents:
                response_list.append(
                    serializers.CourseContentSummaryResponse.model_validate(
                        content
                    ).model_dump()
                )
            return JsonResponse({"course_contents": response_list}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
class ReorderCourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.ReorderCourseContentsRequest.model_validate(
                payload
            )
            course = Course.objects.get(id=kwargs["course_id"])
            course_contents = {
                content.id: content for content in course.coursecontent_set.all()
            }

            with transaction.atomic():
                # Collect valid contents and set temporary negative priorities to avoid conflicts
                contents_to_update = []
                for index, content_id in enumerate(serializer.ordered_content_ids):
                    if content_id in course_contents:
                        content = course_contents[content_id]
                        content.priority = -(
                            index + 1
                        )  # Negative priority to avoid unique constraint conflicts
                        contents_to_update.append(content)

                # Bulk update with negative priorities first
                if contents_to_update:
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

                    # Now set the final positive priorities
                    for index, content in enumerate(contents_to_update):
                        content.priority = index + 1

                    # Final bulk update with correct priorities
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

            return JsonResponse(
                {"message": "Course contents reordered successfully"}, status=200
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
class SingleCourseContentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(id=kwargs["course_content_id"])
            return JsonResponse(
                serializers.CourseContentResponse.model_validate(
                    course_content
                ).model_dump(),
                status=200,
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(id=kwargs["course_content_id"])
            course_content.delete()
            return JsonResponse(
                {"message": "Course content deleted successfully"}, status=200
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.UpdateCourseContentRequest.model_validate(payload)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        try:
            return self._update_course_content_atomic(
                serializer, kwargs["course_content_id"]
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    @transaction.atomic
    def _update_course_content_atomic(
        self, serializer: serializers.UpdateCourseContentRequest, course_content_id: int
    ) -> JsonResponse:
        course_content = CourseContent.objects.get(id=course_content_id)

        if serializer.priority is not None:
            course_content.priority = serializer.priority
        if serializer.waiting_period is not None:
            course_content.waiting_period = serializer.waiting_period.to_seconds()

        if serializer.is_published is not None:
            course_content.is_published = serializer.is_published
            course_content.save()

        if serializer.lesson is not None and course_content.lesson is not None:
            lesson_serializer = serializer.lesson
            lesson = course_content.lesson
            if lesson_serializer.title is not None:
                lesson.title = lesson_serializer.title
            if lesson_serializer.content is not None:
                lesson.content = lesson_serializer.content
            lesson.save()

        if serializer.quiz is not None and course_content.quiz is not None:
            quiz_serializer = serializer.quiz
            quiz = course_content.quiz
            if quiz_serializer.title is not None:
                quiz.title = quiz_serializer.title
            if quiz_serializer.required_score is not None:
                quiz.required_score = quiz_serializer.required_score
            if quiz_serializer.selection_strategy is not None:
                quiz.selection_strategy = quiz_serializer.selection_strategy.value
            if quiz_serializer.deadline_days is not None:
                quiz.deadline_days = quiz_serializer.deadline_days
            if quiz_serializer.questions is not None:
                # Clear existing questions and answers
                quiz.questions.all().delete()
                for question_data in quiz_serializer.questions:
                    question = quiz.questions.create(
                        text=question_data.text, priority=question_data.priority
                    )
                    for answer_data in question_data.answers:
                        question.answers.create(
                            text=answer_data.text, is_correct=answer_data.is_correct
                        )
            quiz.save()

        course_content.save()
        return JsonResponse(
            serializers.CourseContentResponse.model_validate(
                course_content
            ).model_dump(),
            status=200,
        )


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class SingleCourseView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=200,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.UpdateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(course_id=kwargs["course_id"])
            course.save()
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=200,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            course.delete()
            return JsonResponse({"message": "Course deleted successfully"}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class ImapConnectionView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        response_list = []
        imap_connections = ImapConnection.objects.filter(
            organization_id=kwargs["organization_id"]
        )
        for connection in imap_connections:
            response_list.append(
                serializers.ImapConnectionResponse.model_validate(
                    connection
                ).model_dump()
            )
        return JsonResponse({"imap_connections": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateImapConnectionRequest.model_validate(payload)
            imap_connection = serializer.to_django_model(
                organization_id=kwargs["organization_id"]
            )
            imap_connection.save()
            return JsonResponse(
                serializers.ImapConnectionResponse.model_validate(
                    imap_connection
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(is_an_organization_member(), name="get")
@method_decorator(is_platform_admin(), name="post")
class OrganizationsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if request.user.is_superuser:
            organizations = Organization.objects.all()
        else:
            organizations_users = OrganizationUser.objects.select_related(
                "organization"
            ).filter(user_id=request.user.id)
            organizations = [ou.organization for ou in organizations_users]  # type: ignore[assignment]
        response_list = []
        for org in organizations:
            response_list.append(
                serializers.OrganizationResponse.from_django_model(
                    org, request.build_absolute_uri
                ).model_dump()
            )
        return JsonResponse({"organizations": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.CreateOrganizationRequest.model_validate(payload)
            organization = serializer.to_django_model()
            organization.save()
            # Add the creating user as an admin of the organization
            org_user = OrganizationUser(
                user_id=request.user.id, organization_id=organization.id, role="admin"
            )
            org_user.save()
            return JsonResponse(
                serializers.OrganizationResponse.from_django_model(
                    organization,
                    request.build_absolute_uri,
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(is_platform_admin(), name="post")
@method_decorator(is_platform_admin(), name="delete")
class SingleOrganizationView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateOrganizationRequest.model_validate(payload)
            organization = Organization.objects.get(id=kwargs["organization_id"])
            if serializer.name is not None:
                organization.name = serializer.name
            if serializer.description is not None:
                organization.description = serializer.description
            if serializer.logo is not None:
                organization.logo = serializer.logo
            if serializer.remove_logo:
                organization.logo = None
            organization.save()
            return JsonResponse(
                serializers.OrganizationResponse.from_django_model(
                    organization,
                    request.build_absolute_uri,
                ).model_dump(),
                status=200,
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            organization = Organization.objects.get(id=kwargs["organization_id"])
            organization.delete()
            return JsonResponse(
                {"message": "Organization deleted successfully"}, status=200
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
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


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class LearnersView(PaginatedApiMixin, View):
    def get_query_set(self, request: Any) -> models.QuerySet:
        organization_id = self.kwargs["organization_id"]
        qs = Enrollment.objects.filter(course__organization_id=organization_id)
        if "course_id" in request.GET:
            course_id = request.GET["course_id"]
            qs = qs.filter(course_id=course_id)
        if "is_active" in request.GET:
            is_active_str = request.GET["is_active"].lower()
            if is_active_str in ["true", "yes"]:
                qs = qs.filter(status=EnrollmentStatus.ACTIVE)
        if "search" in request.GET:
            search_term = request.GET["search"]
            qs = qs.filter(models.Q(learner__email__icontains=search_term))
        learner_ids = qs.values("learner_id").distinct()
        return Learner.objects.filter(id__in=learner_ids)

    def get_item_serializer_class(self) -> Any:
        return serializers.LearnerResponse


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class SingleLearnerView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            learner = Learner.objects.get(id=kwargs["learner_id"])
            enrollments = Enrollment.objects.filter(learner=learner)
            enroolments_list = []
            for enrollment in enrollments:
                enroolments_list.append(
                    serializers.EnrollmentSummaryResponse(
                        id=enrollment.id,
                        course_title=enrollment.course.title,
                        status=EnrollmentStatus(enrollment.status),
                    )
                )
            return JsonResponse(
                serializers.LearnerDetailResponse(
                    id=learner.id, email=learner.email, enrollments=enroolments_list
                ).model_dump(),
                status=200,
            )
        except Learner.DoesNotExist:
            return JsonResponse({"error": "Learner not found"}, status=404)
        except ValidationError as e:
            logger.error(f"Error in SingleLearnerView: {e.json()}")
            return JsonResponse({"error": "An internal error occurred."}, status=500)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class EnrollmentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            enrollment = Enrollment.objects.get(id=kwargs["enrollment_id"])
            return JsonResponse(
                serializers.EnrollmentResponse.from_django_model(
                    enrollment
                ).model_dump(),
                status=200,
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({"error": "Enrollment not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class EnrollmentsStatisticsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        course_id = kwargs["course_id"]
        a_week_ago = timezone.now() - timedelta(days=7)
        enrollments = (
            Enrollment.objects.filter(course_id=course_id, enrolled_at__gte=a_week_ago)
            .annotate(created_date=TruncDate("enrolled_at"))
            .values(
                "created_date",
            )
            .annotate(count=Count("id"))
            .order_by("created_date")
        )
        dates = [a_week_ago.date() + timedelta(days=i) for i in range(8)]
        enrollments_dict = {
            enrollment["created_date"]: enrollment["count"]
            for enrollment in enrollments
        }
        stats = [
            {"date": date.isoformat(), "count": enrollments_dict.get(date, 0)}
            for date in dates
        ]
        return JsonResponse({"statistics": stats}, status=200)


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


class JobHealthStatus(StrEnum):
    SUCCESS = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


DEFAULT_SUCCESS_THRESHOLD_MINUTES = 15
DEFAULT_WARNING_THRESHOLD_MINUTES = 45


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
        success_threshold = settings.DJANGO_EMAIL_LEARNING.get(
            "JOB_HEALTH_SUCCESS_THRESHOLD_MINUTES", DEFAULT_SUCCESS_THRESHOLD_MINUTES
        )
        warning_threshold = settings.DJANGO_EMAIL_LEARNING.get(
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
