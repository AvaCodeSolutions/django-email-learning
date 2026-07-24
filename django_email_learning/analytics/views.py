import json
from datetime import date, timedelta

from django.db.models import Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from django_email_learning.analytics import serializers
from django_email_learning.analytics.downloads import csv_response
from django_email_learning.decorators import is_an_organization_member
from django_email_learning.models import (
    ContentDelivery,
    CourseContent,
    DeliverySchedule,
    Enrollment,
    EnrollmentStatus,
)
from django_email_learning.models.enums.delivery_status import DeliveryStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRUNC_FN = {
    "day": TruncDate,
    "week": TruncWeek,
    "month": TruncMonth,
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _date_range(request) -> tuple[date, date]:  # type: ignore[no-untyped-def]
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    if not date_to:
        date_to = timezone.now().date()
    if not date_from:
        date_from = date_to - timedelta(days=29)
    return date_from, date_to


def _granularity(request) -> str:  # type: ignore[no-untyped-def]
    value = request.GET.get("granularity", "day")
    return value if value in TRUNC_FN else "day"


def _course_ids(request) -> list[int]:  # type: ignore[no-untyped-def]
    values = request.GET.getlist("course_id")
    try:
        return [int(v) for v in values if v]
    except ValueError:
        return []


def _enrollment_qs(organization_id: int, course_ids: list[int]):  # type: ignore[no-untyped-def]
    qs = Enrollment.objects.filter(course__organization_id=organization_id)
    if course_ids:
        qs = qs.filter(course_id__in=course_ids)
    return qs


def _delivery_schedule_qs(organization_id: int, course_ids: list[int]):  # type: ignore[no-untyped-def]
    qs = DeliverySchedule.objects.filter(delivery__enrollment__course__organization_id=organization_id)
    if course_ids:
        qs = qs.filter(delivery__enrollment__course_id__in=course_ids)
    return qs


def _content_delivery_qs(organization_id: int, course_ids: list[int]):  # type: ignore[no-untyped-def]
    qs = ContentDelivery.objects.filter(enrollment__course__organization_id=organization_id)
    if course_ids:
        qs = qs.filter(enrollment__course_id__in=course_ids)
    return qs


def _json(model: serializers.BaseModel) -> JsonResponse:  # type: ignore[no-untyped-def]
    """Serialise a Pydantic model to a JsonResponse."""
    return JsonResponse(json.loads(model.model_dump_json()))


# ---------------------------------------------------------------------------
# Chart views
# ---------------------------------------------------------------------------


@method_decorator(is_an_organization_member(), name="get")
class EnrollmentsOverTimeView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        date_from, date_to = _date_range(request)
        granularity = _granularity(request)
        course_ids = _course_ids(request)

        trunc = TRUNC_FN[granularity]

        rows = (
            _enrollment_qs(organization_id, course_ids)
            .filter(enrolled_at__date__gte=date_from, enrolled_at__date__lte=date_to)
            .annotate(period=trunc("enrolled_at"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

        response = serializers.EnrollmentsOverTimeResponse(
            data=[serializers.PeriodCount(period=r["period"].isoformat(), count=r["count"]) for r in rows]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class EnrollmentStatusBreakdownView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        rows = (
            _enrollment_qs(organization_id, course_ids)
            .values("course__id", "course__title", "status")
            .annotate(count=Count("id"))
            .order_by("course__title", "status")
        )

        response = serializers.EnrollmentStatusBreakdownResponse(
            data=[
                serializers.CourseStatusCount(
                    course_id=r["course__id"],
                    course_title=r["course__title"],
                    status=r["status"],
                    count=r["count"],
                )
                for r in rows
            ]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class CompletionFunnelView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        contents = CourseContent.objects.filter(
            course__organization_id=organization_id, is_published=True
        ).select_related("course")
        if course_ids:
            contents = contents.filter(course_id__in=course_ids)
        contents = contents.order_by("course__title", "priority")

        delivered_counts = (
            _content_delivery_qs(organization_id, course_ids)
            .filter(delivery_schedules__status=DeliveryStatus.DELIVERED)
            .values("course_content_id")
            .annotate(count=Count("id", distinct=True))
        )
        delivered_map = {r["course_content_id"]: r["count"] for r in delivered_counts}

        response = serializers.CompletionFunnelResponse(
            data=[
                serializers.CompletionFunnelItem(
                    course_content_id=c.id,
                    course_id=c.course_id,
                    course_title=c.course.title,
                    title=c.title,
                    priority=c.priority,
                    type=c.type,
                    learners_reached=delivered_map.get(c.id, 0),
                )
                for c in contents
            ]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class AverageProgressView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        enrollments = list(
            _enrollment_qs(organization_id, course_ids).filter(status=EnrollmentStatus.ACTIVE).select_related("course")
        )
        progress_by_enrollment = Enrollment.bulk_progress_percentages(enrollments)

        course_progress: dict[int, dict] = {}
        for enrollment in enrollments:
            cid = enrollment.course_id
            if cid not in course_progress:
                course_progress[cid] = {
                    "course_id": cid,
                    "course_title": enrollment.course.title,
                    "total": 0,
                    "sum": 0,
                }
            course_progress[cid]["total"] += 1
            course_progress[cid]["sum"] += progress_by_enrollment[enrollment.id]

        response = serializers.AverageProgressResponse(
            data=[
                serializers.AverageProgressItem(
                    course_id=v["course_id"],
                    course_title=v["course_title"],
                    average_progress=round(v["sum"] / v["total"], 1) if v["total"] else 0,
                    active_enrollments=v["total"],
                )
                for v in course_progress.values()
            ]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class TimeToCompleteView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        rows = (
            _enrollment_qs(organization_id, course_ids)
            .filter(status=EnrollmentStatus.COMPLETED, final_state_at__isnull=False)
            .annotate(
                days_to_complete=ExpressionWrapper(
                    F("final_state_at") - F("enrolled_at"),
                    output_field=DurationField(),
                )
            )
            .values("course__id", "course__title", "days_to_complete")
        )

        course_data: dict[int, dict] = {}
        for r in rows:
            cid = r["course__id"]
            if cid not in course_data:
                course_data[cid] = {
                    "course_id": cid,
                    "course_title": r["course__title"],
                    "completions": [],
                }
            if r["days_to_complete"] is not None:
                course_data[cid]["completions"].append(round(r["days_to_complete"].total_seconds() / 86400, 1))

        response = serializers.TimeToCompleteResponse(
            data=[
                serializers.TimeToCompleteItem(
                    course_id=v["course_id"],
                    course_title=v["course_title"],
                    completion_days=v["completions"],
                    average_days=round(sum(v["completions"]) / len(v["completions"]), 1) if v["completions"] else None,
                    total_completions=len(v["completions"]),
                )
                for v in course_data.values()
            ]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class EmailDeliveryOverTimeView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        date_from, date_to = _date_range(request)
        granularity = _granularity(request)
        course_ids = _course_ids(request)

        trunc = TRUNC_FN[granularity]

        rows = (
            _delivery_schedule_qs(organization_id, course_ids)
            .filter(
                status=DeliveryStatus.DELIVERED,
                delivered_at__date__gte=date_from,
                delivered_at__date__lte=date_to,
            )
            .annotate(period=trunc("delivered_at"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

        response = serializers.EmailDeliveryOverTimeResponse(
            data=[serializers.PeriodCount(period=r["period"].isoformat(), count=r["count"]) for r in rows]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class EmailDeliveryStatusBreakdownView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        rows = (
            _delivery_schedule_qs(organization_id, course_ids)
            .values(
                "delivery__enrollment__course__id",
                "delivery__enrollment__course__title",
                "status",
            )
            .annotate(count=Count("id"))
            .order_by("delivery__enrollment__course__title", "status")
        )

        response = serializers.EmailDeliveryStatusBreakdownResponse(
            data=[
                serializers.CourseStatusCount(
                    course_id=r["delivery__enrollment__course__id"],
                    course_title=r["delivery__enrollment__course__title"],
                    status=r["status"],
                    count=r["count"],
                )
                for r in rows
            ]
        )
        return _json(response)


@method_decorator(is_an_organization_member(), name="get")
class EmailOpenRateView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        rows = (
            _content_delivery_qs(organization_id, course_ids)
            .filter(delivery_schedules__status=DeliveryStatus.DELIVERED)
            .values("enrollment__course__id", "enrollment__course__title")
            .annotate(
                total_delivered=Count("id", distinct=True),
                total_opened=Count(
                    "id",
                    filter=Q(opened_at__isnull=False),
                    distinct=True,
                ),
            )
            .order_by("enrollment__course__title")
        )

        response = serializers.EmailOpenRateResponse(
            data=[
                serializers.EmailOpenRateItem(
                    course_id=r["enrollment__course__id"],
                    course_title=r["enrollment__course__title"],
                    total_delivered=r["total_delivered"],
                    total_opened=r["total_opened"],
                    open_rate=round(r["total_opened"] / r["total_delivered"] * 100, 1) if r["total_delivered"] else 0,
                )
                for r in rows
            ]
        )
        return _json(response)


# ---------------------------------------------------------------------------
# Download views
# ---------------------------------------------------------------------------


@method_decorator(is_an_organization_member(only_admin=True), name="get")
class DownloadLearnerProgressView(View):
    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        enrollments = list(
            _enrollment_qs(organization_id, course_ids)
            .select_related("learner", "course")
            .order_by("course__title", "learner__email")
        )
        progress_by_enrollment = Enrollment.bulk_progress_percentages(enrollments)

        last_delivery_map = {}
        schedules = (
            DeliverySchedule.objects.filter(
                delivery__enrollment__course__organization_id=organization_id,
                status=DeliveryStatus.DELIVERED,
            )
            .order_by("delivery__enrollment_id", "-delivered_at")
            .values("delivery__enrollment_id", "delivered_at")
        )
        for s in schedules:
            eid = s["delivery__enrollment_id"]
            if eid not in last_delivery_map:
                last_delivery_map[eid] = s["delivered_at"]

        rows = [
            [
                enrollment.learner.email,
                enrollment.course.title,
                enrollment.enrolled_at.date().isoformat(),
                progress_by_enrollment[enrollment.id],
                enrollment.status,
                last_delivery_map[enrollment.id].isoformat()  # type: ignore[union-attr]
                if last_delivery_map.get(enrollment.id)
                else "",
            ]
            for enrollment in enrollments
        ]

        return csv_response(
            filename="learner_progress.csv",
            headers=[
                "Learner Email",
                "Course",
                "Enrolled Date",
                "Progress %",
                "Status",
                "Last Delivery",
            ],
            rows=rows,
        )


@method_decorator(is_an_organization_member(only_admin=True), name="get")
class DownloadDeliveryLogView(View):
    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        schedules = (
            _delivery_schedule_qs(organization_id, course_ids)
            .select_related(
                "delivery__enrollment__learner",
                "delivery__enrollment__course",
                "delivery__course_content",
            )
            .order_by(
                "delivery__enrollment__course__title",
                "delivery__enrollment__learner__email",
                "time",
            )
        )

        rows = [
            [
                s.delivery.enrollment.learner.email,
                s.delivery.enrollment.course.title,
                s.delivery.course_content.title,
                s.time.date().isoformat(),
                s.delivered_at.date().isoformat() if s.delivered_at else "",
                s.status,
            ]
            for s in schedules
        ]

        return csv_response(
            filename="delivery_log.csv",
            headers=[
                "Learner Email",
                "Course",
                "Content Title",
                "Scheduled Date",
                "Delivered Date",
                "Status",
            ],
            rows=rows,
        )


@method_decorator(is_an_organization_member(only_admin=True), name="get")
class DownloadCompletionSummaryView(View):
    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)

        base_qs = _enrollment_qs(organization_id, course_ids)

        totals = (
            base_qs.values("course__id", "course__title").annotate(total_enrolled=Count("id")).order_by("course__title")
        )

        completed = (
            base_qs.filter(status=EnrollmentStatus.COMPLETED, final_state_at__isnull=False)
            .annotate(
                days=ExpressionWrapper(
                    F("final_state_at") - F("enrolled_at"),
                    output_field=DurationField(),
                )
            )
            .values("course__id", "days")
        )

        completed_map: dict[int, list[float]] = {}
        for r in completed:
            cid = r["course__id"]
            if cid not in completed_map:
                completed_map[cid] = []
            if r["days"] is not None:
                completed_map[cid].append(r["days"].total_seconds() / 86400)

        rows = []
        for t in totals:
            cid = t["course__id"]
            days_list = completed_map.get(cid, [])
            total_completed = len(days_list)
            avg_days = round(sum(days_list) / total_completed, 1) if days_list else ""
            completion_rate = round(total_completed / t["total_enrolled"] * 100, 1) if t["total_enrolled"] else 0
            rows.append(
                [
                    t["course__title"],
                    t["total_enrolled"],
                    total_completed,
                    avg_days,
                    completion_rate,
                ]
            )

        return csv_response(
            filename="completion_summary.csv",
            headers=[
                "Course",
                "Total Enrolled",
                "Completed",
                "Avg Days to Complete",
                "Completion Rate %",
            ],
            rows=rows,
        )
