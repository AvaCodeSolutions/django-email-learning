from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_email_learning.decorators import is_an_organization_member
from django_email_learning.platform.views.base import BasePlatformView
from typing import Dict


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class Learners(BasePlatformView):
    template_name = "platform/learners.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Learners")
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "search_learners": _("Search learners..."),
            "learners_list": _("Learners List"),
            "nor_enrollments_found": _("No enrollments found."),
            "course": _("Course"),
            "status": _("Status"),
            "learner_registered": _("Learner Registered"),
            "learner_verified": _("Learner Verified Email"),
            "lesson_sent": _("Lesson Sent"),
            "quiz_sent": _("Quiz Sent"),
            "assignment_sent": _("Assignment Sent"),
            "quiz_submitted": _("Quiz Submitted"),
            "assignment_submitted": _("Assignment Submitted"),
            "assignment_reviewed": _("Assignment Reviewed"),
            "reviewed_by": _("Reviewed By"),
            "assignment_title": _("Assignment Title"),
            "requesting_changes": _("Requesting Changes"),
            "approved": _("Approved"),
            "rejected": _("Rejected"),
            "course_completed": _("Course Completed"),
            "learner_deactivated": _("Learner Deactivated"),
            "score": _("Score"),
            "result": _("Result"),
            "reason": _("Reason"),
            "passed": _("Passed"),
            "failed": _("Failed"),
            "enrollment_details": _("Enrollment Details"),
            "enrollment_id": _("Enrollment ID"),
            "unverified": _("Unverified"),
            "active": _("Active"),
            "completed": _("Completed"),
            "deactivated": _("Deactivated"),
            "canceled": _("Canceled"),
            "blcoked": _("Blocked"),
            "inactive": _("Inactive"),
            "practice_attempt": _("Practice Attempt"),
            "reminder_sent": _("Reminder Sent"),
            "email_opened": _("Email Opened"),
            "quiz_title": _("Quiz Title"),
            "filter_by_course": _("Filter by Course"),
            "filter_by_status": _("Filter by Status"),
            "all_courses": _("All Courses"),
            "all_statuses": _("All Statuses"),
            "reset_filters": _("Reset Filters"),
            "progress": _("Progress"),
            "no_learners_found": _("No learners found."),
        }
