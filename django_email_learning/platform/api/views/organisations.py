import json
import uuid

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from pydantic import ValidationError

from django_email_learning.decorators import (
    accessible_for,
    is_an_organization_member,
    is_platform_admin,
)
from django_email_learning.models import (
    Organization,
    OrganizationUser,
)
from django_email_learning.platform.api import serializers

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(is_an_organization_member(), name="get")
@method_decorator(is_platform_admin(), name="post")
class OrganizationsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if request.user.is_superuser:
            organizations = Organization.objects.all()
        else:
            organizations_users = OrganizationUser.objects.select_related("organization").filter(
                user_id=request.user.id
            )
            organizations = [ou.organization for ou in organizations_users]  # type: ignore[assignment]
        response_list = []
        for org in organizations:
            response_list.append(
                serializers.OrganizationResponse.from_django_model(org, request.build_absolute_uri).model_dump()
            )
        return JsonResponse({"organizations": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.CreateOrganizationRequest.model_validate(payload)
            organization = serializer.to_django_model()
            organization.save()
            # Add the creating user as an admin of the organization
            org_user = OrganizationUser(user_id=request.user.id, organization_id=organization.id, role="admin")
            org_user.save()
            return JsonResponse(
                serializers.OrganizationResponse.from_django_model(
                    organization,
                    request.build_absolute_uri,
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin"}), name="post")
@method_decorator(accessible_for(roles={"admin"}), name="get")
class OrganizationUsersView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.AddOrganizationUserRequest.model_validate(payload)
            organization = Organization.objects.get(id=kwargs["organization_id"])
            org_user = OrganizationUser(
                user_id=serializer.user_id,
                organization=organization,
                role=serializer.role,
                display_name=serializer.display_name,
                photo=serializer.photo,
            )
            org_user.save()
            return JsonResponse(
                serializers.OrganizationUserResponse.from_django_model(org_user, request).model_dump(),
                status=201,
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_users = OrganizationUser.objects.filter(organization_id=kwargs["organization_id"])
        response_list = []
        for org_user in organization_users:
            response_list.append(serializers.OrganizationUserResponse.from_django_model(org_user, request).model_dump())
        return JsonResponse({"organization_users": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin"}), name="delete")
@method_decorator(accessible_for(roles={"admin"}), name="post")
class SingleOrganizationUserView(View):
    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            org_user = OrganizationUser.objects.get(id=kwargs["user_id"])
            org_user.delete()
            return JsonResponse({"message": "Organization user removed successfully"}, status=200)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"error": "Organization user not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateOrganizationUserRequest.model_validate(payload)
            org_user = OrganizationUser.objects.get(
                organization_id=kwargs["organization_id"], user_id=kwargs["user_id"]
            )
            org_user.role = serializer.role
            org_user.display_name = serializer.display_name
            org_user.photo = serializer.photo
            org_user.save()
            return JsonResponse(
                serializers.OrganizationUserResponse.from_django_model(org_user, request).model_dump(),
                status=200,
            )
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"error": "Organization user not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin"}), name="post")
@method_decorator(is_platform_admin(), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class SingleOrganizationView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateOrganizationRequest.model_validate(payload)
            organization = Organization.objects.get(id=kwargs["organization_id"])
            if serializer.name is not None:
                organization.name = serializer.name
            if serializer.description is not None:
                organization.description = serializer.description
            if serializer.logo is not None:
                organization.logo = serializer.logo
            if serializer.remove_logo:
                organization.logo = None
            if serializer.website is not None:
                organization.website = serializer.website
            if serializer.youtube_channel is not None:
                organization.youtube_channel = serializer.youtube_channel
            if serializer.linkedin_page is not None:
                organization.linkedin_page = serializer.linkedin_page
            if serializer.is_public is not None:
                organization.is_public = serializer.is_public
            organization.save()
            return JsonResponse(
                serializers.OrganizationResponse.from_django_model(
                    organization,
                    request.build_absolute_uri,
                ).model_dump(),
                status=200,
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            organization = Organization.objects.get(id=kwargs["organization_id"])
            organization.delete()
            return JsonResponse({"message": "Organization deleted successfully"}, status=200)
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            organization = Organization.objects.get(id=kwargs["organization_id"])
            return JsonResponse(
                serializers.OrganizationResponse.from_django_model(
                    organization,
                    request.build_absolute_uri,
                ).model_dump(),
                status=200,
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator((is_an_organization_member(only_admin=True)), name="post")
class GetOrCreateUserByEmail(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        serializer = serializers.GetOrCreateUserRequest.model_validate(payload)
        try:
            email = serializer.email
            organization_id = serializer.organization_id
            user = User.objects.filter(email=email).first()
            if not user:
                user = User.objects.create_user(username=email, email=email, password=uuid.uuid4().hex)
                form = PasswordResetForm(data={"email": email})
                if form.is_valid():
                    form.save(
                        request=request,
                        use_https=request.is_secure(),
                        from_email=DJANGO_EMAIL_LEARNING_SETTINGS.get("FROM_EMAIL", settings.DEFAULT_FROM_EMAIL),
                        email_template_name="emails/password_reset.txt",
                        html_email_template_name="emails/password_reset.html",
                        extra_email_context={"organization": Organization.objects.get(id=organization_id).name},
                    )
                else:
                    raise ValueError("Failed to send password reset email to the new user.")
            return JsonResponse(serializers.UserResponse.model_validate(user).model_dump(), status=200)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)
