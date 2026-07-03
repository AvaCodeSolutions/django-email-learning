from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import get_language_info, gettext as _

from django_email_learning.decorators import is_an_organization_member
from django_email_learning.models import (
    Course,
    Newsletter,
)
from django_email_learning.platform.views.base import (
    QUIZ_DEFAULTS,
    BasePlatformView,
)


@method_decorator(login_required, name="dispatch")
class Courses(BasePlatformView):
    template_name = "platform/courses.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Courses")
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "actions": _("Actions"),
            "all": _("All"),
            "enable_course": _("Enable COURSE_NAME"),
            "disable_course": _("Disable COURSE_NAME"),
            "delete_course": _("Delete COURSE_NAME"),
            "enabled": _("Enabled"),
            "disabled": _("Disabled"),
            "title": _("Title"),
            "slug": _("Slug"),
            "filter": _("Filter"),
            "add_course": _("Add a Course"),
            "course_status": _("Course Status"),
            "cancel": _("Cancel"),
            "delete": _("Delete"),
            "create": _("Create"),
            "continue": _("Continue"),
            "update": _("Update"),
            "course_title": _("Course Title"),
            "course_description": _("Course Description"),
            "target_audience": _("Target Audience"),
            "course_is_public": _("Public Course"),
            "course_is_public_helper_text": _(
                "Public courses are visible on your organization's public pages."
                " Turn this off to keep the course private."
            ),
            "course_send_certificate": _("Send Certificate on Completion"),
            "course_send_certificate_helper_text": _(
                "When enabled, learners will receive a certificate email upon completing this course."
            ),
            "external_references": _("External References"),
            "add_external_reference": _("Add Reference"),
            "external_references_helper_text": _(
                "Add up to 10 optional links for learners, such as docs, repos, or supporting resources."
            ),
            "reference_name": _("Reference Name"),
            "reference_url": _("Reference URL"),
            "remove": _("Remove"),
            "course_slug": _("Course Slug"),
            "course_language": _("Course Language"),
            "slug_tooltip": _(
                "The slug is a unique identifier for the course used in URLs and API endpoints."
                " It should be lowercase, contain no spaces (use hyphens instead), and be unique"
                " across all courses for your organization. Once set, the slug cannot be changed."
            ),
            "slug_no_space": _("Slug cannot contain spaces. Use hyphens instead."),
            "add_newsletter": _("Link Newsletter"),
            "newsletter_tooltip": _(
                "Link this course to a newsletter. Subscribers of the linked newsletter can be automatically"
                " enrolled when the auto-enroll feature is enabled."
            ),
            "new_newsletter": _("New Newsletter"),
            "newsletter": _("Newsletter"),
            "newsletter_title": _("Title"),
            "newsletter_language": _("Language"),
            "newsletter_create_error": _("Failed to create newsletter. Please try again."),
            "add_imap_connection": _("Add IMAP Connection"),
            "imap_connection_tooltip": _(
                "You don't need an IMAP connection to build your course, but you will need one if you want"
                " your users to interact via email. For example, they can enroll, verify their enrollmnent"
                " or drop out just by sending a message. This is a great solution if your audience has"
                " limited platform access."
            ),
            "new_imap_connection": _("New IMAP Connection"),
            "imap_connection": _("IMAP Connection"),
            "add": _("Add"),
            "email": _("Email"),
            "password": _("Password"),
            "server": _("Server"),
            "port": _("Port"),
            "private": _("Private"),
            "course_enable_confirmation": _("Are you sure you want to enable the course COURSE_NAME?"),
            "course_disable_confirmation": _("Are you sure you want to disable the course COURSE_NAME?"),
            "course_delete_confirmation": _("Are you sure you want to delete the course COURSE_NAME?"),
            "title_required_helper_text": _("The course title is required."),
            "description_required_helper_text": _("The course description is required."),
            "reference_name_required_helper_text": _("A reference name is required when a reference link is provided."),
            "reference_url_required_helper_text": _(
                "A valid reference URL is required when a reference name is provided."
            ),
            "slug_required_helper_text": _("The course slug is required."),
            "language_required_helper_text": _("The course language is required."),
            "email_required_helper_text": _("The email is required."),
            "password_required_helper_text": _("The password is required."),
            "server_required_helper_text": _("The server is required."),
            "port_required_helper_text": _("The port is required."),
            "invalid_port_helper_text": _("The port must be a valid number."),
            "invalid_email_helper_text": _("The email must be a valid email address."),
            "total_enrollments": _("Total Enrollments"),
            "upload_button_label": _("Upload Image"),
            "remove_image": _("Remove Image"),
            "uploaded_image_alt": _("Course Image"),
            "add_folder_helper_text": _(
                "Add folders to fetch emails from. The 'inbox' folder is required and will always be included."
            ),  # noqa: E501
            "add_instructors": _("Add Instructors"),
            "instructors_tooltip": _(
                "Assign instructors from your organization to this course."
                " Instructors can review and approve learner assignment submissions."
            ),
            "select_instructors": _("Select Instructors"),
            "new_instructor": _("New Instructor"),
            "instructor_email": _("Instructor Email"),
            "instructor_display_name": _("Display Name"),
            "instructor_display_name_required": _("Display name is required for instructors."),
            "instructor_photo": _("Instructor Photo"),
            "add_instructor": _("Add Instructor"),
            "instructor_add_failed": _("Failed to add instructor. Please try again."),
            "none": _("None"),
            "imap_connection_failed": _("Failed to create IMAP connection. Please try again."),
            "folder_name_cannot_be_empty": _("Folder name cannot be empty."),
            "folder_already_added": _("Folder already added."),
            "add_folder": _("Add folder"),
            "inbox_required_helper_text": _("'inbox' is required and cannot be removed."),
            "server_error": _("Server error occurred. Please try again later."),
        }


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class CourseView(BasePlatformView):
    template_name = "platform/course.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        course = Course.objects.get(pk=self.kwargs["course_id"])
        context["appContext"]["courseId"] = course.id
        context["appContext"]["courseTitle"] = course.title
        context["appContext"]["courseLanguage"] = course.language
        context["appContext"]["courseEnabled"] = course.enabled
        context["appContext"]["customComponent"] = None
        context["appContext"]["quizDefaults"] = {
            "limitedAttempts": QUIZ_DEFAULTS.get("LIMITED_ATTEMPTS", True),
            "isBlocking": QUIZ_DEFAULTS.get("IS_BLOCKING", True),
            "hasDeadline": QUIZ_DEFAULTS.get("HAS_DEADLINE", True),
            "reminderIntervalDays": QUIZ_DEFAULTS.get("REMINDER_INTERVAL_DAYS", 3),
        }
        context["appContext"]["direction"] = "rtl" if get_language_info(course.language)["bidi"] else "ltr"
        organization_id = self.get_or_set_active_organization()
        context["appContext"]["newsletters"] = list(
            Newsletter.objects.filter(organization_id=organization_id).values("id", "title")
        )
        context["page_title"] = _("Course: %(title)s") % {"title": course.title}
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "actions": _("Actions"),
            "course_disabled": _("Disabled"),
            "course_disabled_banner": _("This course is disabled. Learners cannot be enrolled until you enable it."),
            "enroll_learner": _("Enroll Learner"),
            "enrollment_success": _("Learner enrolled successfully."),
            "imported_from_google_success": _("Learners imported from Google Workspace successfully."),
            "manual_email": _("Manual Email"),
            "from_google_workspace": _("Import from Google Workspace"),
            "google_workspace_description": _(
                "If you are an administrator of a Google Workspace domain, you can import users from your"
                " domain into the platform and enroll them in this course."
            ),
            "authorize_description": _(
                "We need read-only access to your Google Workspace user directory to get started."
            ),
            "authorize_button": _("Authorize with Google"),
            "published": _("Published"),
            "type": _("Type"),
            "waiting_time": _("Send Delay"),
            "title": _("Title"),
            "add_quiz": _("Add Quiz"),
            "add_assignment": _("Add Assignment"),
            "send_lesson_to_yourself": _("Send it to yourself"),
            "add_lesson": _("Add Lesson"),
            "lesson": _("Lesson"),
            "quiz": _("Quiz"),
            "assignment": _("Assignment"),
            "add": _("Add"),
            "new_lesson": _("New Lesson"),
            "update_lesson": _("Update Lesson"),
            "new_quiz": _("New Quiz"),
            "update_quiz": _("Update Quiz"),
            "editing": _("Editing..."),
            "edit_with_ai": _("Edit with AI"),
            "lesson_title": _("Lesson Title"),
            "blocking_quiz": _("Blocking Quiz"),
            "blocking_assignment": _("Blocking Assignment"),
            "blocking_quiz_tooltip": _(
                "If enabled, learners must pass the quiz to continue receiving course content."
                " For practice quizzes that don't gate content, you can disable this option"
                " so learners can continue with the course regardless of their quiz performance."
            ),
            "blocking_assignment_tooltip": _(
                "If enabled, learners must submit the assignment, and the assignment must be approved by"
                " an instructor before they can continue receiving course content."
            ),
            "lesson_waiting_tooltip": _(
                "How long to wait after the previous item is sent before delivering this lesson."
                " Each delay is relative to the previous item, not to enrollment."
            ),
            "upload": _("Upload"),
            "uploaded_image_preview": _("Uploaded image preview"),
            "add_image_to_editor": _("Add image to editor"),
            "remove_uploaded_image": _("Remove uploaded image"),
            "confirm_delete_uploaded_image": _("Confirm image deletion"),
            "delete_uploaded_image_warning": _(
                "Please confirm this image is not used anywhere else. Deleting it will break existing links."
            ),
            "uploaded_image_used_in_editor_error": _(
                "This image is already used in the editor content. Remove it from the content before deleting the file."
            ),
            "uploaded_image_delete_failed": _("Failed to delete image file. Please try again."),
            "days": _("Days"),
            "hours": _("Hours"),
            "back": _("Back"),
            "cancel": _("Cancel"),
            "delete": _("Delete"),
            "save_lesson": _("Save Lesson"),
            "lesson_saved_success": _("Lesson content saved successfully."),
            "lesson_unsaved_changes_hint": _("You have unsaved changes."),
            "save_quiz": _("Save Quiz"),
            "quiz_title": _("Quiz Title"),
            "assignment_title": _("Assignment Title"),
            "new_assignment": _("New Assignment"),
            "update_assignment": _("Update Assignment"),
            "assignment_submission_required": _(
                "At least one type of submission is required for the assignment."
                " Please enable text submission, file submission, or both."
            ),
            "add_question": _("Add Question"),
            "quiz_settings": _("Quiz Settings"),
            "waiting_period": _("Send Delay"),
            "limited_attempts": _("Limited Attempts"),
            "unlimited_attempts": _("Unlimited Attempts"),
            "two_attempts": _("2 Attempts"),
            "practice_quiz": _("Practice Quiz"),
            "limited_attempts_tooltip": _(
                "If limited attempts is enabled, learners only have 2 attempts to pass the quiz."
                " After 2 failed attempts, they will fail the course and need to restart it."
                " If limited attempts is disabled, learners can retry the quiz as many times as needed"
                " until they pass."
            ),
            "quiz_2_attempts_sub_note": _(
                "Learners only have 2 attempts to pass the quiz. After 2 failed attempts,"
                " they will fail the course and need to restart it."
            ),
            "quiz_unlimited_attempts_sub_note": _(
                "Learners can retry the quiz as many times as needed until they pass."
            ),
            "quiz_waiting_tooltip": _("Time to wait after the previous content delivery before sending this quiz"),
            "required_score": _("Required Score to Pass (%)"),
            "score_tooltip": _("Minimum percentage score required to pass this quiz"),
            "period": _("Period"),
            "period_tooltip": _(
                "How long to wait after the previous item is sent before delivering this quiz."
                " Each delay is relative to the previous item, not to enrollment."
            ),
            "percentage": _("Percentage"),
            "quiz_deadline": _("Deadline to Complete Quiz"),
            "assignment_deadline": _("Deadline to Complete Assignment"),
            "deadline_tooltip": _("Maximum time allowed to complete the quiz or assignment"),
            "question_selection_strategy": _("Selection Strategy"),
            "question_selection_strategy_tooltip": _(
                "Choose how questions are selected for each quiz attempt. If the total number of questions"
                " is fewer than 6, all questions will be used even if 'Random Questions' is selected."
            ),
            "all_questions": _("All Questions"),
            "random_questions": _("Random Questions"),
            "question": _("Question"),
            "add_option": _("Add Option"),
            "option_text": _("Option Text"),
            "options": _("Options"),
            "correct_answer": _("Correct Answer"),
            "quiz_title_empty": _("Quiz title cannot be empty."),
            "at_least_one_question": _("Quiz must have at least one question"),
            "at_least_two_options": _("Question QUESTION_NUMBER must have at least two answer options"),
            "at_least_one_correct": _("Question QUESTION_NUMBER must have at least one correct answer"),
            "fix_errors": _("Please fix the errors in the form before submitting."),
            "lesson_title_required": _("Lesson title is required."),
            "lesson_content_required": _("Lesson content is required."),
            "delete_content_confirmation": _("Are you sure you want to delete the content: CONTENT_TITLE?"),
            "total_enrollments": _("Total Enrollments"),
            "unverified": _("Unverified"),
            "active": _("Active"),
            "deactivated": _("Deactivated"),
            "completed": _("Completed"),
            "enrollments_distribution": _("Enrollments Distribution"),
            "weekly_enrollments": _("Weekly Enrollments"),
            "tab_manage_course_content": _("Manage Course Content"),
            "tab_submitted_assignments": _("Submitted Assignments"),
            "tab_course_analytics": _("Course Analytics"),
            "submitted_assignments_tab_info": _("Submitted assignments will be available in this section."),
            "pending_filter_chip": _("Pending Review"),
            "show_pending_only": _("Show Pending Only"),
            "submitted_at": _("Submitted At"),
            "reviewed_at": _("Reviewed At"),
            "reviewed_by": _("Reviewed By"),
            "status": _("Status"),
            "pending_review": _("Pending Review"),
            "approved": _("Approved"),
            "rejected": _("Rejected"),
            "requesting_changes": _("Requesting Changes"),
            "no_submitted_assignments": _("No submitted assignments found."),
            "submitted_assignment_details": _("Submitted Assignment Details"),
            "feedbacks": _("Feedbacks"),
            "no_feedbacks_yet": _("No feedbacks yet."),
            "unable_to_load_submission_details": _("Unable to load submission details."),
            "course_analytics_tab_info": _("Course analytics are shown below."),
            "unsaved_changes_warning": _("You have unsaved changes. Are you sure you want to leave without saving?"),
            "close_without_saving": _("Close without saving"),
            "required_score_blocking": _(
                "A blocking quiz must have a required score greater than 0% to ensure learners"
                " can pass and continue with the course."
            ),
            "deadline_cannot_be_zero": _(
                "Deadline cannot be 0 when deadline is enabled. Set a positive number of days or disable the deadline."
            ),
            "reminder_interval_days": _("Reminder Interval Days"),
            "reminder_interval_days_tooltip": _(
                "When a quiz does not have a deadline, you can define a reminder interval to specify"
                " how often learners should receive reminder emails to complete the quiz."
                " Setting to 0 means no reminder emails will be sent."
            ),
            "assignment_description": _("Assignment Description"),
            "assignment_description_required": _("Assignment description is required."),
            "assignment_title_required": _("Assignment title is required."),
            "save_assignment": _("Save Assignment"),
            "assignment_saved_success": _("Assignment saved successfully."),
            "assignment_waiting_tooltip": _(
                "How long to wait after the previous item is sent before delivering this assignment."
                " Each delay is relative to the previous item, not to enrollment."
            ),
            "no_deadline": _("No Deadline"),
            "requires_text_submission": _("Requires Text Submission"),
            "requires_file_submission": _("Requires File Submission"),
            "save_failed": _("Unable to save. Please try again."),
            "question_cannot_be_empty": _("Question QUESTION_NUMBER cannot be empty."),
            "error_creating_quiz": _("Error creating quiz. Please try again."),
            "error_updating_quiz": _("Error updating quiz. Please try again."),
            "reminder_interval_days_required": _(
                "Reminder interval days must be greater than 0 when reminders are enabled."
            ),
        }

    def get_app_context(self) -> Dict[str, Any]:
        return {}
