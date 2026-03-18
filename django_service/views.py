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
