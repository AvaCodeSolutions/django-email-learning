from django import forms
from django.contrib import admin

from django_email_learning.models import (
    AssignmentFeedback,
    AssignmentSubmission,
    ContentDelivery,
    Course,
    DeliverySchedule,
    Enrollment,
    ImapConnection,
    InboxFolder,
    JobExecution,
    Learner,
    Lesson,
    Newsletter,
    NewsletterSubscriber,
    OrganizationUser,
    Quiz,
    QuizSubmission,
    Sendout,
)
from django_email_learning.oauth_integrations.models import Session


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
            obj.password = obj.decrypt_password(obj.password)
        return obj


class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "state")
    list_filter = ("state", "created_at")


class JobExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "job_name", "status", "started_at")
    search_fields = ("job_name", "status")
    list_filter = ("job_name", "status", "started_at")


admin.site.register(JobExecution, JobExecutionAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(ImapConnection, ImapConnectionAdmin)
admin.site.register(OrganizationUser)
admin.site.register(Enrollment)
admin.site.register(ContentDelivery)
admin.site.register(Learner)
admin.site.register(DeliverySchedule)
admin.site.register(QuizSubmission)
admin.site.register(InboxFolder)
admin.site.register(Lesson)
admin.site.register(Quiz)
admin.site.register(Session, SessionAdmin)
admin.site.register(AssignmentSubmission)
admin.site.register(AssignmentFeedback)
admin.site.register(Newsletter)
admin.site.register(Sendout)
admin.site.register(NewsletterSubscriber)
