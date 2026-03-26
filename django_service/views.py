from django.views.generic import TemplateView
from django_email_learning.models import Lesson, Quiz, CourseContent
from django_email_learning.platform.views import CourseView
from django_email_learning.platform.serializers import WebComponent


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
        ]:
            raise ValueError(
                "Invalid template name. Allowed values are: 'certificate_form', 'enrollment_verified', 'enrollment_verification', 'lesson', 'password_reset', 'quiz'."
            )

        return [f"emails/{template_name}.html"]

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        lesson = Lesson.objects.first()
        quiz = Quiz.objects.first()
        content = (
            CourseContent.objects.filter(lesson=lesson).first() if lesson else None
        )
        return {
            "course_title": "Example Course",
            "organization_name": "Example Organization",
            "course_image_url": "/static/src/assets/sample.jpg",
            "support_imap_interface": False,
            "verification_link": "https://example.com/verify",
            "lesson": lesson,
            "quiz": quiz,
            "unsubscribe_link": "https://example.com/unsubscribe",
            "protocol": "https",
            "domain": "example.com",
            "uid": "sampleuid",
            "token": "sampletoken",
            "progress": 40,
            "next_content": content.get_next() if content else None,
        }
