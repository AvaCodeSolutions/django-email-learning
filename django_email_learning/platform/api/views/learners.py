import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from django.db import models
from django.db.models import Count, Prefetch
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.models import (
    Certificate,
    Course,
    DeliverySchedule,
    Enrollment,
    EnrollmentStatus,
    Learner,
)
from django_email_learning.platform.api import serializers
from django_email_learning.platform.api.pagniated_api_mixin import PaginatedApiMixin
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
from django_email_learning.services.manual_delivery_service import (
    ManualDeliveryOutcome,
    send_delivery_schedule_now,
)

logger = logging.getLogger(__name__)


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="get")
class LearnersView(PaginatedApiMixin, View):
    # Stashed on the instance so serialize_item can read it without re-parsing the request.
    _course_id: str | None = None

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
        if "status" in request.GET:
            status_value = request.GET["status"]
            try:
                qs = qs.filter(status=EnrollmentStatus(status_value))
            except ValueError:
                pass
        if "search" in request.GET:
            search_term = request.GET["search"]
            qs = qs.filter(models.Q(learner__email__icontains=search_term))
        learner_ids = qs.values("learner_id").distinct()
        learner_qs = Learner.objects.filter(id__in=learner_ids)

        course_id = request.GET.get("course_id")
        self._course_id = course_id
        if course_id:
            # Prefetch the single enrollment for this course so serialize_item
            # can access status and progress_percentage without extra DB queries.
            learner_qs = learner_qs.prefetch_related(
                Prefetch(
                    "enrollments",
                    queryset=Enrollment.objects.filter(course_id=course_id),
                    to_attr="_course_enrollment",
                )
            )
        return learner_qs

    def get_item_serializer_class(self) -> Any:
        return serializers.LearnerResponse

    def serialize_item(self, item: Any, request: Any) -> dict:
        data = serializers.LearnerResponse.model_validate(item).model_dump()
        if self._course_id:
            enrollments: list = getattr(item, "_course_enrollment", [])
            enrollment = enrollments[0] if enrollments else None
            if enrollment:
                data["enrollment_status"] = enrollment.status
                data["enrollment_progress"] = enrollment.progress_percentage()
        return data


@method_decorator(accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get")
class SingleLearnerView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            learner = Learner.objects.get(id=kwargs["learner_id"], organization_id=kwargs["organization_id"])
            enrollments = Enrollment.objects.filter(learner=learner)
            enroolments_list = []
            for enrollment in enrollments:
                certificate = Certificate.objects.filter(enrollment=enrollment).first()
                certificate_url = None
                if certificate:
                    certificate_url = request.build_absolute_uri(
                        reverse(
                            "django_email_learning:personalised:certificate",
                            kwargs={"certificate_number": certificate.certificate_number},
                        )
                    )
                enroolments_list.append(
                    serializers.EnrollmentSummaryResponse(
                        id=enrollment.id,
                        course_title=enrollment.course.title,
                        status=EnrollmentStatus(enrollment.status),
                        progress=enrollment.progress_percentage(),
                        certificate_url=certificate_url,
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


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="post")
class EnrollmentsView(PaginatedApiMixin, View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateEnrollmentRequest.model_validate(payload)
            try:
                course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
            except Course.DoesNotExist:
                return JsonResponse({"error": "Course not found"}, status=404)
            command = EnrollCommand(
                email=serializer.learner_email,
                course_slug=course.slug,
                organization_id=kwargs["organization_id"],
                no_verification=True,  # skip verification email for manual enrollments through the API
            )
            try:
                command.execute()
            except BlockedEmailError as e:
                error_reference = uuid.uuid4()
                logger.warning(f"{str(e)} (error_id: {error_reference})")
                return JsonResponse({"error": "Access denied", "error_id": str(error_reference)}, status=403)
            except LearnerCapExceededError as e:
                error_reference = uuid.uuid4()
                logger.warning(f"{str(e)} (error_id: {error_reference})")
                return JsonResponse({"error": "Access denied", "error_id": str(error_reference)}, status=403)
            except EnrollmentAlreadyExistsError as e:
                logger.warning(f"Enrollment already exists for {serializer.learner_email}: {str(e)}")
                return JsonResponse({"error": "Enrollment already exists"}, status=409)

            enrollment = Enrollment.objects.get(learner__email=serializer.learner_email, course_id=kwargs["course_id"])
            verify_command = VerifyEnrollmentCommand(
                enrollment_id=enrollment.id,
                verification_code=enrollment.activation_code,  # type: ignore[arg-type]
            )
            verify_command.execute()
            enrollment.refresh_from_db()
            return JsonResponse(
                serializers.EnrollmentResponse.from_django_model(enrollment).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class EnrollmentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            enrollment = Enrollment.objects.get(
                id=kwargs["enrollment_id"], course__organization_id=kwargs["organization_id"]
            )
            return JsonResponse(
                serializers.EnrollmentResponse.from_django_model(enrollment).model_dump(),
                status=200,
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({"error": "Enrollment not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(accessible_for(roles={"admin"}), name="post")
class SendDeliveryScheduleNowView(View):
    """Sends one scheduled content delivery immediately.

    Admin-only: it puts an email in a learner's inbox and advances their
    enrollment, which is a heavier action than the read access the rest of the
    enrollment views grant. Changing the schedule's time would not do the same
    job - the delivery job runs on a cron, so the content would still go out
    whenever that next fires.
    """

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            enrollment = Enrollment.objects.get(
                id=kwargs["enrollment_id"], course__organization_id=kwargs["organization_id"]
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({"error": "Enrollment not found"}, status=404)

        try:
            delivery_schedule = DeliverySchedule.objects.get(
                id=kwargs["delivery_schedule_id"],
                delivery__enrollment=enrollment,
            )
        except DeliverySchedule.DoesNotExist:
            return JsonResponse({"error": "Delivery schedule not found"}, status=404)

        result = send_delivery_schedule_now(delivery_schedule)

        if result.outcome == ManualDeliveryOutcome.NOT_SCHEDULED:
            return JsonResponse(
                {"error": "Delivery is no longer scheduled", "delivery_status": result.delivery_status},
                status=409,
            )
        if result.outcome == ManualDeliveryOutcome.FAILED:
            logger.error(
                f"Manual send of DeliverySchedule {delivery_schedule.id} failed with status {result.delivery_status}."
            )
            return JsonResponse(
                {"error": "Delivery failed", "delivery_status": result.delivery_status},
                status=500,
            )

        return JsonResponse(
            {"status": result.delivery_status, "delivery_schedule_id": delivery_schedule.id},
            status=200,
        )


@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class EnrollmentsStatisticsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        course_id = kwargs["course_id"]
        a_week_ago = timezone.now() - timedelta(days=7)
        enrollments = (
            Enrollment.objects.filter(
                course_id=course_id,
                course__organization_id=kwargs["organization_id"],
                enrolled_at__gte=a_week_ago,
            )
            .annotate(created_date=TruncDate("enrolled_at"))
            .values(
                "created_date",
            )
            .annotate(count=Count("id"))
            .order_by("created_date")
        )
        dates = [a_week_ago.date() + timedelta(days=i) for i in range(8)]
        enrollments_dict = {enrollment["created_date"]: enrollment["count"] for enrollment in enrollments}
        stats = [{"date": date.isoformat(), "count": enrollments_dict.get(date, 0)} for date in dates]
        return JsonResponse({"statistics": stats}, status=200)
