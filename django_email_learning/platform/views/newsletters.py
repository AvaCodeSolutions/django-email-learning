from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django_email_learning.models import Newsletter
from django_email_learning.decorators import is_an_organization_member
from django_email_learning.platform.views.base import BasePlatformView
from typing import Dict


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class NewsletterDetailView(BasePlatformView):
    template_name = "platform/newsletter.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        newsletter = Newsletter.objects.get(
            pk=self.kwargs["newsletter_id"],
            organization_id=self.kwargs["organization_id"],
        )
        context["appContext"]["newsletterId"] = newsletter.id
        context["appContext"]["newsletterTitle"] = newsletter.title
        context["appContext"]["organizationId"] = newsletter.organization_id
        context["page_title"] = _("Newsletter: %(title)s") % {"title": newsletter.title}
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "scheduled": _("Scheduled"),
            "sent": _("Sent"),
            "all": _("All"),
            "subject": _("Subject"),
            "scheduled_at": _("Scheduled At"),
            "status": _("Status"),
            "no_sendouts": _("No sendouts yet."),
            "create_sendout": _("Create Sendout"),
            "sendout_subject": _("Subject"),
            "sendout_body": _("Body"),
            "sendout_scheduled_at": _("Scheduled At"),
            "sendout_subject_required": _("Subject is required."),
            "sendout_body_required": _("Body is required."),
            "sendout_scheduled_at_required": _("Scheduled date is required."),
            "sendout_create_error": _("Failed to create sendout. Please try again."),
            "cancel": _("Cancel"),
            "save": _("Save"),
            "actions": _("Actions"),
            "retry_count": _("Retries"),
            "update_sendout": _("Update Sendout"),
            "editing": _("Editing..."),
            "edit_with_ai": _("Edit with AI"),
            "upload": _("Upload"),
            "upload_images": _("Upload Images"),
            "no_uploaded_images": _("No uploaded images yet."),
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
            "newsletter_subscribers": _("Subscribers"),
        }


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(), name="dispatch")
class NewsletterSubscribersView(BasePlatformView):
    template_name = "platform/newsletter_subscribers.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        newsletter = Newsletter.objects.get(
            pk=self.kwargs["newsletter_id"],
            organization_id=self.kwargs["organization_id"],
        )
        context["appContext"]["newsletterId"] = newsletter.id
        context["appContext"]["newsletterTitle"] = newsletter.title
        context["appContext"]["organizationId"] = newsletter.organization_id
        context["page_title"] = _("Subscribers: %(title)s") % {
            "title": newsletter.title
        }
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "subscribers": _("Subscribers"),
            "email": _("Email"),
            "subscribed_at": _("Subscribed At"),
            "no_subscribers": _("No subscribers yet."),
            "delete": _("Delete"),
            "confirm_delete": _("Confirm Delete"),
            "delete_subscriber_warning": _(
                "Are you sure you want to remove this subscriber?"
            ),
            "cancel": _("Cancel"),
            "export_csv": _("Export CSV"),
            "actions": _("Actions"),
        }
