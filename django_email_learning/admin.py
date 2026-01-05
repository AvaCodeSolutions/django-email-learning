from django.contrib import admin
from django import forms
from .models import (
    Course,
    ImapConnection,
    Organization,
    OrganizationUser,
    BlockedEmail,
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
            obj.imap_password = obj.decrypt_password(obj.imap_password)
        return obj


admin.site.register(Course, CourseAdmin)
admin.site.register(ImapConnection, ImapConnectionAdmin)
admin.site.register(Organization)
admin.site.register(BlockedEmail)
admin.site.register(OrganizationUser)
admin.site.register(Enrollment)
admin.site.register(ContentDelivery)
admin.site.register(Learner)
admin.site.register(DeliverySchedule)
admin.site.register(QuizSubmission)
