from typing import Dict

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from django_email_learning.decorators import is_an_organization_member
from django_email_learning.platform.views.base import BasePlatformView


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(allow_active_org_fallback=True), name="dispatch")
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
            "decision_sent": _("Decision Sent"),
            "gate_reached": _("Reached Gate"),
            "gate_unlocked": _("Gate Unlocked"),
            "gate_unlock_source_api": _("Unlocked through the API"),
            "gate_unlock_source_admin": _("Unlocked by %(user)s"),
            "gate_unlock_source_timeout": _("Timed out and continued"),
            "gate_unlock_source_integration": _("Unlocked by an integration"),
            "waiting": _("Waiting"),
            "waiting_at_gate": _("Waiting at gate: %(gate)s"),
            "path_status_waiting": _("Waiting"),
            "unlock_gate": _("Unlock"),
            "unlock_gate_title": _("Unlock this gate?"),
            "unlock_gate_confirmation": _(
                "The learner moves past %(gate)s and on to the rest of the course, as if it had been unlocked "
                "through the API."
            ),
            "confirm_unlock_gate": _("Unlock"),
            "unlocking": _("Unlocking..."),
            "gate_unlock_failed": _("The gate could not be unlocked."),
            "waiting_for_confirmation": _("Waiting at the enrollment gate"),
            "enrollment_confirmed": _("Enrollment Confirmed"),
            "enrollment_confirmed_source_api": _("Confirmed through the API"),
            "enrollment_confirmed_source_admin": _("Confirmed by %(user)s"),
            "enrollment_email_opened": _("Opened Enrollment Email"),
            "enrollment_email": _("Enrollment email"),
            "verification_email": _("Verification email"),
            "enrollment_reminder_sent": _("Enrollment Reminder Sent"),
            "enrollment_reminder_opened": _("Opened Enrollment Reminder"),
            "verification_reminder": _("Verification reminder"),
            "enrollment_reminder": _("Enrollment reminder"),
            "confirm_enrollment": _("Confirm enrollment"),
            "confirm_enrollment_title": _("Confirm this enrollment?"),
            "confirm_enrollment_confirmation": _(
                "The enrollment becomes active, the learner is sent the welcome email and their first content is"
                " scheduled, as if the enrollment gate had been unlocked through the API."
            ),
            "confirming": _("Confirming..."),
            "verify_enrollment": _("Verify enrollment"),
            "verify_enrollment_title": _("Verify this enrollment?"),
            "verify_enrollment_confirmation": _(
                "The enrollment becomes active without the learner following their verification link. They are"
                " sent the welcome email and their first content is scheduled. Only do this if you know the email"
                " address is theirs."
            ),
            "enrollment_confirm_failed": _("The enrollment could not be confirmed."),
            "gate_expired": _("Gate timed out"),
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
            "next_delivery": _("Next delivery"),
            "learner_path": _("Path taken"),
            "path_status_delivered": _("Sent"),
            "path_status_scheduled": _("Scheduled"),
            "path_status_not_sent": _("Not sent"),
            "main_path": _("Main path"),
            "send_now": _("send now"),
            "sending": _("Sending..."),
            "content_sent_successfully": _("Content sent."),
            "content_send_failed": _("The content could not be sent."),
            "delivery_no_longer_scheduled": _("This delivery is no longer scheduled."),
            "revoked": _("Revoked"),
            "cancel_enrollment": _("Cancel enrollment"),
            "cancel_enrollment_title": _("Cancel this enrollment?"),
            "cancel_enrollment_confirmation": _(
                "The learner stops receiving this course immediately and any content still "
                "scheduled for them is canceled. This cannot be undone."
            ),
            "keep_enrollment": _("Keep enrollment"),
            "confirm_cancel_enrollment": _("Cancel enrollment"),
            "canceling": _("Canceling..."),
            "enrollment_cancel_failed": _("The enrollment could not be canceled."),
        }
