from django.contrib import admin
from django import forms
from django_email_learning.models import (
    Lesson,
    Quiz,
    Course,
    ImapConnection,
    InboxFolder,
    OrganizationUser,
    Enrollment,
    ContentDelivery,
    Learner,
    DeliverySchedule,
    QuizSubmission,
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
            obj.password = obj.decrypt_password(obj.password)
        return obj


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
