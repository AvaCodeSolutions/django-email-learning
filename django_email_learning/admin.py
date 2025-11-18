from django.contrib import admin
from django import forms
from django.http import HttpRequest
from .models import (
    Course,
    ImapConnection,
    Quiz,
    Lesson,
    Question,
    Answer,
    CourseContent,
    Organization,
    BlockedEmail,
)


class ImapConnectionAdminForm(forms.ModelForm):
    class Meta:
        model = ImapConnection
        fields = "__all__"
        widgets = {
            "password": forms.PasswordInput(
                render_value=True,
            ),
        }


class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "enabled")
    search_fields = ("title",)
    list_filter = ("enabled",)


class ImapConnectionAdmin(admin.ModelAdmin):
    list_display = ("email", "server", "port")
    search_fields = ("email", "server")
    list_filter = ("port",)
    form = ImapConnectionAdminForm

    def get_object(self, *args, **kwargs) -> ImapConnection | None:  # type: ignore[no-untyped-def]
        obj = super().get_object(*args, **kwargs)
        if obj:
            obj.imap_password = obj.decrypt_password(obj.imap_password)
        return obj


class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "required_score", "is_published")
    search_fields = ("title",)
    list_filter = ("is_published",)

    def get_fields(
        self, request: HttpRequest, obj: Quiz | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            return ("title", "required_score")
        return ("title", "required_score", "is_published")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1


class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ("text", "quiz")
    search_fields = ("text",)
    list_filter = ("quiz",)


class CourseContentAdmin(admin.ModelAdmin):
    list_filter = ("course", "type")
    list_display = ("course", "priority", "type", "get_content_title")
    ordering = ("course", "priority")

    def get_content_title(self, obj: CourseContent) -> str | None:
        if obj.type == "lesson" and obj.lesson:
            return obj.lesson.title
        elif obj.type == "quiz" and obj.quiz:
            return obj.quiz.title
        return None


admin.site.register(Course, CourseAdmin)
admin.site.register(ImapConnection, ImapConnectionAdmin)
admin.site.register(Lesson)
admin.site.register(Quiz, QuizAdmin)
admin.site.register(CourseContent, CourseContentAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer)
admin.site.register(Organization)
admin.site.register(BlockedEmail)
