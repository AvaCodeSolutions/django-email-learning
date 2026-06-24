from django.views.generic import TemplateView
from django_email_learning.models import Assignment, Lesson, Quiz, CourseContent
from django_email_learning.platform.views import CourseView
from django_email_learning.platform.serializers import WebComponent
from django.utils import timezone


class CustomComponentCourseView(CourseView):
    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)

        custom_component = WebComponent(
            html="<button id='custom-btn'>Clicked 0 times!</button>",
            style_url="/static/styles/custom-component.css",
            script_url="/static/scripts/custom-component.js",
        )
        context["appContext"]["customComponent"] = custom_component.model_dump()
        return context


class EmailTemplatePreview(TemplateView):
    def get_template_names(self) -> list[str]:
        template_name = self.request.GET.get("template")
        if not template_name:
            raise ValueError("The 'template' query parameter is required.")
        if template_name not in [
            "certificate_form",
            "enrollment_verified",
            "enrollment_verification",
            "lesson",
            "password_reset",
            "quiz",
            "assignment",
            "assignment_reminder",
            "assignment_review",
            "quiz_reminder",
            "deactivation_deadline_passed",
            "newsletter_sendout",
        ]:
            raise ValueError(
                "Invalid template name. Allowed values are: 'certificate_form', 'enrollment_verified', "
                "'enrollment_verification', 'lesson', 'password_reset', 'quiz', 'assignment', "
                "'assignment_reminder', 'assignment_review', 'quiz_reminder', 'deactivation_deadline_passed', 'newsletter_sendout'."
            )

        return [f"emails/{template_name}.html"]

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        lesson = Lesson.objects.first()
        quiz = Quiz.objects.first()
        assignment = Assignment.objects.first()
        content = (
            CourseContent.objects.filter(lesson=lesson).first() if lesson else None
        )
        return {
            "course_title": "Example Course",
            "course_slug": "example-course",
            "organization_name": "Example Organization",
            "course_image_url": "/static/src/assets/sample.jpg",
            "support_imap_interface": True,
            "verification_link": "https://example.com/verify",
            "verification_code": "ABC123",
            "imap_email_address": "test@test.com",
            "subject": "Welcome to the course!",
            "lesson": lesson,
            "quiz": quiz,
            "unsubscribe_link": "https://example.com/unsubscribe",
            "protocol": "https",
            "domain": "example.com",
            "uid": "sampleuid",
            "token": "sampletoken",
            "progress": 40,
            "message": "Your assignment has been reviewed and changes have been requested. Please review the feedback and update your submission accordingly.",
            "change_requested": True,
            "title_prefix": "Change Requested",
            "feedback": {
                "provider": {
                    "name": "John Doe",
                    "photo": "https://i.pravatar.cc/50?img=12",  # Replace with a mock photo object if needed
                },
                "comment": "Please update your code to handle edge cases.",
            },
            "link": "https://example.com/assignment/1",
            "newsletter_title": "Weekly Newsletter",
            "body": "Welcome to our weekly newsletter! Here are the latest updates and news from our organization.",
            "deadline_time": timezone.now(),
            "unsubscribe_url": "https://example.com/unsubscribe",
            "assignment": assignment,
            "next_content": content.get_next() if content else None,
            "content_title": "assignment programming exercise",
        }
