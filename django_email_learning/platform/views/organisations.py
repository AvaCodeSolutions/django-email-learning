from typing import Dict

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from django_email_learning.decorators import is_an_organization_member
from django_email_learning.models import ApiKeyScope, Organization
from django_email_learning.platform.views.base import BasePlatformView


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(only_admin=True, allow_active_org_fallback=True), name="dispatch")
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
            "description_max_length_helper_text": _("Description must be 1000 characters or fewer."),
            "description_char_limit_helper_text": _("COUNT/1000 characters used."),
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
            "organization_brand_color": _("Brand Color"),
            "organization_brand_color_label": _("Brand color"),
            "organization_brand_color_helper_text": _(
                "Used for buttons on your public pages and as the default color for your embed widget."
            ),
            "requires_text_submission": _("Requires Text Submission"),
            "requires_file_submission": _("Requires File Submission"),
            "uploaded_image_alt": _("Organization Logo"),
            "organization_logo_alt": _("Organization Logo"),
            "logo_upload_failed": _("Logo upload failed. Please try again."),
            "private": _("Private"),
            "are_you_sure_delete_org": _(
                'Are you sure you want to delete the organization "ORGANIZATION_NAME"?'
                " All course content and users in this organization will also be deleted."
            ),
            "invalid_url_helper_text": _("Enter a valid URL starting with http:// or https://"),
            "website": _("Website"),
            "linkedin_page": _("LinkedIn page"),
            "youtube_channel": _("YouTube channel"),
            "facebook_page": _("Facebook page"),
            "instagram": _("Instagram"),
            "tiktok": _("TikTok"),
            "twitter_x": _("X (Twitter)"),
            "whatsapp_channel": _("WhatsApp channel"),
            "telegram_channel": _("Telegram channel"),
            "substack": _("Substack"),
            "social_links": _("Social links"),
            "add_social_link": _("Add link"),
            "social_link_platform": _("Platform"),
            "social_link_url": _("URL"),
            "remove_social_link": _("Remove link"),
        }


@method_decorator(login_required, name="dispatch")
@method_decorator(is_an_organization_member(only_admin=True), name="dispatch")
class SingleOrganization(BasePlatformView):
    template_name = "platform/organization.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        organization = Organization.objects.get(pk=self.kwargs["organization_id"])
        context["organization"] = organization
        context["page_title"] = _("Organization: %(name)s") % {"name": organization.name}
        context["appContext"]["organizationId"] = organization.id
        # Sourced from the enum the API validates against, so the choices the
        # form offers can't drift from the scopes a key may actually carry.
        context["appContext"]["apiKeyScopes"] = [
            {"value": value, "label": str(label)} for value, label in ApiKeyScope.choices
        ]
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
            "admin_role_description": _("Full access, including creating users and organizations."),
            "email": _("Email"),
            "delete_user_with_email": _("Deleting USER_EMAIL"),
            "user_delete_confirmation": _("Are you sure you want to remove USER_EMAIL from this organization?"),
            "actions": _("Actions"),
            "cannot_add_member": _("Adding new members is not allowed."),
            "cannot_remove_self": _("You can't remove your own membership. Ask another admin to do this for you."),
            "cannot_change_own_role": _("You can't change your own role. Ask another admin to do this for you."),
            "delete_note": _(
                "Note: Removing a user from this organization will not delete their account."
                " To permanently delete the user's account, you must do so separately within the Django Admin"
            ),
            "cancel": _("Cancel"),
            "delete": _("Delete"),
            "upload_button_label": _("Upload Image"),
            "remove_image": _("Remove Image"),
            "uploaded_image_alt": _("User Photo"),
            "general_info": _("General Info"),
            "edit": _("Edit"),
            "name": _("Name"),
            "description": _("Description"),
            "name_required": _("Name is required."),
            "description_required": _("Description is required."),
            "description_max_length_helper_text": _("Description must be 1000 characters or fewer."),
            "description_char_limit_helper_text": _("COUNT/1000 characters used."),
            "error_try_again": _("An error occurred. Please try again."),
            "create": _("Create"),
            "update": _("Update"),
            "organization_is_public": _("Public Organization"),
            "organization_is_public_helper_text": _(
                "Public organizations are visible on your public pages. Turn this off to keep the organization private."
            ),
            "organization_brand_color": _("Brand Color"),
            "organization_brand_color_label": _("Brand color"),
            "organization_brand_color_helper_text": _(
                "Used for buttons on your public pages and as the default color for your embed widget."
            ),
            "invalid_url_helper_text": _("Enter a valid URL starting with http:// or https://"),
            "website": _("Website"),
            "linkedin_page": _("LinkedIn page"),
            "youtube_channel": _("YouTube channel"),
            "facebook_page": _("Facebook page"),
            "instagram": _("Instagram"),
            "tiktok": _("TikTok"),
            "twitter_x": _("X (Twitter)"),
            "whatsapp_channel": _("WhatsApp channel"),
            "telegram_channel": _("Telegram channel"),
            "substack": _("Substack"),
            "social_links": _("Social links"),
            "add_social_link": _("Add link"),
            "social_link_platform": _("Platform"),
            "social_link_url": _("URL"),
            "remove_social_link": _("Remove link"),
            "organization_logo_alt": _("Organization Logo"),
            "logo_upload_failed": _("Logo upload failed. Please try again."),
            "members": _("Members"),
            "newsletters": _("Newsletters"),
            "no_newsletters": _("No newsletters yet."),
            "create_newsletter": _("Create Newsletter"),
            "newsletter_title": _("Title"),
            "newsletter_language": _("Language"),
            "newsletter_subscribers": _("Subscribers"),
            "newsletter_title_required": _("Title is required."),
            "newsletter_create_error": _("Failed to create newsletter. Please try again."),
            "newsletter_duplicate_error": _("A newsletter with this title already exists."),
            "newsletter_delete_confirmation": _(
                "Are you sure you want to delete NEWSLETTER_TITLE?"
                " This will also remove all its subscribers and scheduled sendouts."
            ),
            "view_public_organization_page": _("Public page"),
            "copy_public_organization_link": _("Copy public organization link"),
            "public_organization_link_copied": _("Link copied!"),
            "api_keys": _("API Keys"),
            "no_api_keys": _("No API keys yet."),
            "create_api_key": _("Create API Key"),
            "api_key_name": _("Name"),
            "api_key_name_required": _("Name is required."),
            "api_key_scopes": _("Scopes"),
            "api_key_scopes_required": _("Select at least one scope."),
            "api_key_expires_at": _("Expires on"),
            "api_key_expires_at_helper_text": _("Optional. The key never expires if left blank."),
            "api_key_create_error": _("Failed to create the API key. Please try again."),
            "key_id": _("Key ID"),
            "status": _("Status"),
            "active": _("Active"),
            "revoked": _("Revoked"),
            "expired": _("Expired"),
            "last_used": _("Last Used"),
            "never_used": _("Never used"),
            "created_by": _("Created By"),
            "created_at": _("Created At"),
            "revoke": _("Revoke"),
            "confirm_revocation": _("Confirm Revocation"),
            "are_you_sure_revoke_key": _(
                "Are you sure you want to revoke API_KEY_NAME? Anything using this key will stop working immediately."
            ),
            "copy": _("Copy"),
            "copied": _("Copied"),
            "done": _("Done"),
            "new_api_key_created": _("New API key created"),
            "copy_key_now_warning": _(
                "Copy this key now. For security it is stored hashed, so this is the only time it can be shown."
            ),
            "api_keys_intro": _(
                "API keys let your own systems act on this organization's data — enrolling a learner from"
                " your signup flow, for example. Each key carries only the scopes you grant it and acts"
                " solely on this organization."
            ),
        }
