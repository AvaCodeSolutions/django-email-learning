import logging
from django.apps import apps
from django.conf.global_settings import LANGUAGES
from django.views.generic import TemplateView, View
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.utils.translation import get_language_info, get_language
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.urls import reverse
from django_email_learning.models import Organization, OrganizationUser, Course
from django_email_learning.decorators import (
    is_platform_admin,
    is_an_organization_member,
)
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE
from django_email_learning.services import jwt_service
from typing import Dict, Any
from django.conf import settings


DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
AI_CONFIGURATIONS: dict = DJANGO_EMAIL_LEARNING_SETTINGS.get("AI", {})
QUIZ_DEFAULTS: dict = DJANGO_EMAIL_LEARNING_SETTINGS.get("QUIZ_DEFAULTS", {})


@method_decorator(login_required, name="dispatch")
class BasePlatformView(TemplateView):
    """Base view for all platform views with shared context"""

    def get_context_data(self, **kwargs) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context.update(self.get_shared_context())
        return context

    def get_shared_context(self) -> Dict[str, Any]:
        """Get shared context for all platform views"""
        active_organization_id = self.get_or_set_active_organization()
        if self.request.user.is_superuser:
            role = "admin"
        else:
            role = OrganizationUser.objects.get(  # type: ignore[misc]
                user=self.request.user,
                organization_id=active_organization_id,
            ).role

        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)

        return {
            "appContext": {
                "apiBaseUrl": reverse("django_email_learning:api_platform:root")[:-1],
                "platformBaseUrl": reverse("django_email_learning:platform:root")[:-1],
                "analyticsBaseUrl": {
                    "base": f"{reverse('django_email_learning:api_analytics:enrollments_over_time', kwargs={'organization_id': active_organization_id}).rsplit('/enrollments', 1)[0]}",
                    "orgId": active_organization_id,
                },
                "sidebarCustomComponent": {
                    "scriptUrl": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("SCRIPT_URL"),
                    "componentTag": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("COMPONENT_TAG"),
                    "styleUrl": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("STYLE_URL"),
                },
                "userRole": role,
                "direction": "rtl" if lang_info["bidi"] else "ltr",
                "isPlatformAdmin": (
                    self.request.user.is_superuser
                    or (
                        self.request.user.is_authenticated
                        and getattr(self.request.user, "has_platform_admin_role", False)
                    )
                ),
                "isInstructor": (
                    self.request.user.is_superuser
                    or (
                        OrganizationUser.objects.filter(
                            user=self.request.user,
                            organization_id=active_organization_id,
                            role="instructor",
                        ).exists()  # type: ignore[misc]
                    )
                ),
                "aiTextEditingModel": AI_CONFIGURATIONS.get("TEXT_EDITING_MODEL"),
                "customLogo": {
                    "horizontalLight": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("HORIZONTAL_LOCKUP", {})
                    .get("LIGHT_BACKGROUND"),
                    "horizontalDark": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("HORIZONTAL_LOCKUP", {})
                    .get("DARK_BACKGROUND"),
                    "verticalLight": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("VERTICAL_LOCKUP", {})
                    .get("LIGHT_BACKGROUND"),
                    "verticalDark": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("VERTICAL_LOCKUP", {})
                    .get("DARK_BACKGROUND"),
                }
                if DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO")
                else None,
                "isOrganizationAdmin": (
                    self.request.user.is_superuser
                    or (
                        OrganizationUser.objects.filter(
                            user=self.request.user,
                            organization_id=active_organization_id,
                            role="admin",
                        ).exists()  # type: ignore[misc]
                    )
                ),
                "localeMessages": {
                    "organizations": _("Organizations"),
                    "course_management": _("Course Management"),
                    "learners": _("Learners"),
                    "analytics": _("Analytics"),
                    "settings": _("Settings"),
                    "api_keys": _("API Keys"),
                    "content_delivery_job": _("Content Delivery Job"),
                    "last_run": _("Last Run:"),
                    "never_run": _("This job has never been executed."),
                    "content_delivery_tooltip": _(
                        "This job should run on a regular schedule to ensure timely content delivery. Configure a cron job or cloud scheduler to execute it at appropriate intervals, such as every five minutes."
                    ),
                }
                | self.get_locale_messages(),
                "languageOptions": [
                    {"value": code, "label": name} for code, name in LANGUAGES
                ],
            },
            "activeOrganizationId": active_organization_id,
            "favicon": DJANGO_EMAIL_LEARNING_SETTINGS.get("FAVICON"),
        }

    def get_locale_messages(self) -> Dict[str, str]:
        return {}

    def get_or_set_active_organization(self) -> str:
        org = self.request.session.get("active_organization_id")
        if org:
            return org

        member = self.request.user.memberships.first()  # type: ignore[union-attr]
        logging.debug(f"User memberships: {member}")
        if member:
            org = member.organization
        elif self.request.user.is_superuser:
            org = Organization.objects.first()

        if org:
            logging.debug(f"Active organization: {org}")
            self.request.session["active_organization_id"] = str(org.id)
            return str(org.id)

        raise Exception("No active organization found for the user.")


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
                "Public courses are visible on your organization's public pages. Turn this off to keep the course private."
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
                "The slug is a unique identifier for the course used in URLs and API endpoints. It should be lowercase, contain no spaces (use hyphens instead), and be unique across all courses for your organization. Once set, the slug cannot be changed."
            ),
            "slug_no_space": _("Slug cannot contain spaces. Use hyphens instead."),
            "add_imap_connection": _("Add IMAP Connection"),
            "imap_connection_tooltip": _(
                "You don't need an IMAP connection to build your course, but you will need one if you want your users to interact via email. For example, they can enroll, verify their enrollmnent or drop out just by sending a message. This is a great solution if your audience has limited platform access."
            ),
            "new_imap_connection": _("New IMAP Connection"),
            "imap_connection": _("IMAP Connection"),
            "add": _("Add"),
            "email": _("Email"),
            "password": _("Password"),
            "server": _("Server"),
            "port": _("Port"),
            "private": _("Private"),
            "course_enable_confirmation": _(
                "Are you sure you want to enable the course COURSE_NAME?"
            ),
            "course_disable_confirmation": _(
                "Are you sure you want to disable the course COURSE_NAME?"
            ),
            "course_delete_confirmation": _(
                "Are you sure you want to delete the course COURSE_NAME?"
            ),
            "title_required_helper_text": _("The course title is required."),
            "description_required_helper_text": _(
                "The course description is required."
            ),
            "reference_name_required_helper_text": _(
                "A reference name is required when a reference link is provided."
            ),
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
                "Assign instructors from your organization to this course. Instructors can review and approve learner assignment submissions."
            ),
            "select_instructors": _("Select Instructors"),
            "new_instructor": _("New Instructor"),
            "instructor_email": _("Instructor Email"),
            "instructor_display_name": _("Display Name"),
            "instructor_display_name_required": _(
                "Display name is required for instructors."
            ),
            "instructor_photo": _("Instructor Photo"),
            "add_instructor": _("Add Instructor"),
            "instructor_add_failed": _("Failed to add instructor. Please try again."),
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
        context["appContext"]["customComponent"] = None
        context["appContext"]["quizDefaults"] = {
            "limitedAttempts": QUIZ_DEFAULTS.get("LIMITED_ATTEMPTS", True),
            "isBlocking": QUIZ_DEFAULTS.get("IS_BLOCKING", True),
            "hasDeadline": QUIZ_DEFAULTS.get("HAS_DEADLINE", True),
            "reminderIntervalDays": QUIZ_DEFAULTS.get("REMINDER_INTERVAL_DAYS", 3),
        }
        context["appContext"]["direction"] = (
            "rtl" if get_language_info(course.language)["bidi"] else "ltr"
        )
        context["appContext"]["showGoogleWorkspaceImport"] = bool(
            DJANGO_EMAIL_LEARNING_SETTINGS.get("GOOGLE_OAUTH_CLIENT_ID")
        ) and apps.is_installed("django_email_learning.oauth_integrations")
        context["page_title"] = _("Course: %(title)s") % {"title": course.title}
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "actions": _("Actions"),
            "enroll_learner": _("Enroll Learner"),
            "enrollment_success": _("Learner enrolled successfully."),
            "imported_from_google_success": _(
                "Learners imported from Google Workspace successfully."
            ),
            "manual_email": _("Manual Email"),
            "from_google_workspace": _("Import from Google Workspace"),
            "google_workspace_description": _(
                "If you are an administrator of a Google Workspace domain, you can import users from your domain into the platform and enroll them in this course."
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
                "If enabled, learners must pass the quiz to continue receiving course content. For practice quizzes that don't gate content, "
                "you can disable this option so learners can continue with the course regardless of their quiz performance."
            ),
            "blocking_assignment_tooltip": _(
                "If enabled, learners must submit the assignment, and the assignment must be approved by an instructor before they can continue receiving course content."
            ),
            "lesson_waiting_tooltip": _(
                "How long to wait after the previous item is sent before delivering this lesson. Each delay is relative to the previous item, not to enrollment."
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
            "uploaded_image_delete_failed": _(
                "Failed to delete image file. Please try again."
            ),
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
                "At least one type of submission is required for the assignment. Please enable text submission, file submission, or both."
            ),
            "add_question": _("Add Question"),
            "quiz_settings": _("Quiz Settings"),
            "waiting_period": _("Send Delay"),
            "limited_attempts": _("Limited Attempts"),
            "unlimited_attempts": _("Unlimited Attempts"),
            "two_attempts": _("2 Attempts"),
            "practice_quiz": _("Practice Quiz"),
            "limited_attempts_tooltip": _(
                "If limited attempts is enabled, learners only have 2 attempts to pass the quiz. "
                "After 2 failed attempts, they will fail the course and need to restart it. If limited attempts is disabled, "
                "learners can retry the quiz as many times as needed until they pass."
            ),
            "quiz_2_attempts_sub_note": _(
                "Learners only have 2 attempts to pass the quiz. After 2 failed attempts, they will fail the course and need to restart it."
            ),
            "quiz_unlimited_attempts_sub_note": _(
                "Learners can retry the quiz as many times as needed until they pass."
            ),
            "quiz_waiting_tooltip": _(
                "Time to wait after the previous content delivery before sending this quiz"
            ),
            "required_score": _("Required Score to Pass (%)"),
            "score_tooltip": _("Minimum percentage score required to pass this quiz"),
            "period": _("Period"),
            "period_tooltip": _(
                "How long to wait after the previous item is sent before delivering this quiz. Each delay is relative to the previous item, not to enrollment."
            ),
            "percentage": _("Percentage"),
            "quiz_deadline": _("Deadline to Complete Quiz"),
            "assignment_deadline": _("Deadline to Complete Assignment"),
            "deadline_tooltip": _(
                "Maximum time allowed to complete the quiz or assignment"
            ),
            "question_selection_strategy": _("Selection Strategy"),
            "question_selection_strategy_tooltip": _(
                "Choose how questions are selected for each quiz attempt. If the total number of questions is fewer than 6, all questions will be used even if 'Random Questions' is selected."
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
            "at_least_two_options": _(
                "Question QUESTION_NUMBER must have at least two answer options"
            ),
            "at_least_one_correct": _(
                "Question QUESTION_NUMBER must have at least one correct answer"
            ),
            "fix_errors": _("Please fix the errors in the form before submitting."),
            "lesson_title_required": _("Lesson title is required."),
            "lesson_content_required": _("Lesson content is required."),
            "delete_content_confirmation": _(
                "Are you sure you want to delete the content: CONTENT_TITLE?"
            ),
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
            "submitted_assignments_tab_info": _(
                "Submitted assignments will be available in this section."
            ),
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
            "unable_to_load_submission_details": _(
                "Unable to load submission details."
            ),
            "course_analytics_tab_info": _("Course analytics are shown below."),
            "unsaved_changes_warning": _(
                "You have unsaved changes. Are you sure you want to leave without saving?"
            ),
            "close_without_saving": _("Close without saving"),
            "required_score_blocking": _(
                "A blocking quiz must have a required score greater than 0% to ensure learners can pass and continue with the course."
            ),
            "deadline_cannot_be_zero": _(
                "Deadline cannot be 0 when deadline is enabled. Set a positive number of days or disable the deadline."
            ),
            "reminder_interval_days": _("Reminder Interval Days"),
            "reminder_interval_days_tooltip": _(
                "When a quiz does not have a deadline, you can define a reminder interval to specify "
                "how often learners should receive reminder emails to complete the quiz. Setting to 0 means no reminder emails will be sent."
            ),
            "assignment_description": _("Assignment Description"),
            "assignment_description_required": _("Assignment description is required."),
            "assignment_title_required": _("Assignment title is required."),
            "save_assignment": _("Save Assignment"),
            "assignment_saved_success": _("Assignment saved successfully."),
            "assignment_waiting_tooltip": _(
                "How long to wait after the previous item is sent before delivering this assignment. Each delay is relative to the previous item, not to enrollment."
            ),
            "no_deadline": _("No Deadline"),
            "requires_text_submission": _("Requires Text Submission"),
            "requires_file_submission": _("Requires File Submission"),
            "save_failed": _("Unable to save. Please try again."),
        }

    def get_app_context(self) -> Dict[str, Any]:
        return {}


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(only_admin=True), name="dispatch")
class Organizations(BasePlatformView):
    template_name = "platform/organizations.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Organizations")
        context["appContext"]["defaultOrgSetting"] = {"isPublic": True}
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "add_organization": _("Add an Organization"),
            "actions": _("Actions"),
            "name": _("Name"),
            "description": _("Description"),
            "name_required": _("Name is required."),
            "description_required": _("Description is required."),
            "error_try_again": _("An error occurred. Please try again."),
            "upload_button_label": _("Upload Logo"),
            "create_organization": _("Create Organization"),
            "cancel": _("Cancel"),
            "delete": _("Delete"),
            "confirm_deletion": _("Confirm Deletion"),
            "remove_image": _("Remove Logo"),
            "create": _("Create"),
            "update": _("Update"),
            "organization_is_public": _("Public Organization"),
            "organization_is_public_helper_text": _(
                "Public organizations are visible on your public pages. Turn this off to keep the organization private."
            ),
            "requires_text_submission": _("Requires Text Submission"),
            "requires_file_submission": _("Requires File Submission"),
            "uploaded_image_alt": _("Organization Logo"),
            "private": _("Private"),
            "are_you_sure_delete_org": _(
                'Are you sure you want to delete the organization "ORGANIZATION_NAME"? All course content and users in this organization will also be deleted.'
            ),
        }


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(only_admin=True), name="dispatch")
class SingleOrganization(BasePlatformView):
    template_name = "platform/organization.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        organization = Organization.objects.get(pk=self.kwargs["organization_id"])
        context["organization"] = organization
        context["page_title"] = _("Organization: %(name)s") % {
            "name": organization.name
        }
        context["appContext"]["organizationId"] = organization.id
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "no_users_in_organization": _("No users in this organization yet."),
            "add_users_to_organization": _("Add user to organization"),
            "add_user": _("Add User"),
            "edit_user": _("Edit User"),
            "change_user_role": _("Change User Role"),
            "user": _("User"),
            "role": _("Role"),
            "display_name": _("Display Name"),
            "display_name_required": _("Display name is required for instructors."),
            "photo": _("Photo"),
            "admin": _("Admin"),
            "editor": _("Editor"),
            "instructor": _("Instructor"),
            "viewer": _("Viewer"),
            "viewer_role_description": _("Read-only access to course content."),
            "editor_role_description": _("Can create and edit course content."),
            "instructor_role_description": _(
                "All editor permissions, plus access to learners and assignment review and approval."
            ),
            "admin_role_description": _(
                "Full access, including creating users and organizations."
            ),
            "email": _("Email"),
            "delete_user_with_email": _("Deleting USER_EMAIL"),
            "user_delete_confirmation": _(
                "Are you sure you want to remove USER_EMAIL from this organization?"
            ),
            "actions": _("Actions"),
            "delete_note": _(
                "Note: Removing a user from this organization will not delete their account. To permanently delete the user's account, you must do so separately within the Django Admin"
            ),
            "cancel": _("Cancel"),
            "delete": _("Delete"),
            "upload_button_label": _("Upload Image"),
            "remove_image": _("Remove Image"),
            "uploaded_image_alt": _("User Photo"),
        }


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
            "quiz_title": _("Quiz Title"),
            "filter_by_course": _("Filter by Course"),
            "filter_by_status": _("Filter by Status"),
            "all_courses": _("All Courses"),
            "all_statuses": _("All Statuses"),
            "reset_filters": _("Reset Filters"),
            "progress": _("Progress"),
            "no_learners_found": _("No learners found."),
        }


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
            "are_you_sure_delete_key": _(
                "Are you sure you want to delete this API key?"
            ),
            "created_by": _("Created By"),
            "cancel": _("Cancel"),
            "confirm_deletion": _("Confirm Deletion"),
            "api_key_intro": _(
                "API keys allow external applications to interact with the platform and execute jobs. This is ideal for using cloud scheduling or third-party integrations instead of managing local cron jobs. You can create, view, and manage your keys below."
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
            logging.error(
                "Token is missing required fields. Decoded token: %s", decoded_token
            )
            return HttpResponseBadRequest("Missing 'file_path' or 'org_id' in token.")

        if (
            not request.user.is_superuser
            and not OrganizationUser.objects.filter(
                user=request.user,
                organization_id=org_id,
                role__in=["admin", "instructor"],
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
                "Shows how many learners received each piece of content. The bar length is relative to the content with the most deliveries, so you can quickly see where learners drop off."
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
