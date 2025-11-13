from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.utils import IntegrityError
from django.http import JsonResponse
from pydantic import ValidationError
from django_email_learning.api import serializers
from django_email_learning.models import (
    Course,
    ImapConnection,
    OrganizationUser,
    Organization,
)
from django_email_learning.decorators import (
    accessible_for,
    is_an_organization_member,
    is_platform_admin,
)
import json


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class CourseView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(
                organization_id=kwargs["organization_id"]
            )
            course.save()
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        courses = Course.objects.filter(organization_id=kwargs["organization_id"])
        enabled = request.GET.get("enabled")
        if enabled is not None:
            if enabled.lower() in ["true", "yes"]:
                courses = courses.filter(enabled=True)
            elif enabled.lower() in ["false", "no"]:
                courses = courses.filter(enabled=False)

        response_list = []
        for course in courses:
            response_list.append(
                serializers.CourseResponse.model_validate(course).model_dump()
            )
        return JsonResponse({"courses": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class SingleCourseView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=200,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.UpdateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(course_id=kwargs["course_id"])
            course.save()
            return JsonResponse(
                serializers.CourseResponse.model_validate(course).model_dump(),
                status=200,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            course.delete()
            return JsonResponse({"message": "Course deleted successfully"}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
class ImapConnectionView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        response_list = []
        imap_connections = ImapConnection.objects.filter(
            organization_id=kwargs["organization_id"]
        )
        for connection in imap_connections:
            response_list.append(
                serializers.ImapConnectionResponse.model_validate(
                    connection
                ).model_dump()
            )
        return JsonResponse({"imap_connections": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateImapConnectionRequest.model_validate(payload)
            imap_connection = serializer.to_django_model(
                organization_id=kwargs["organization_id"]
            )
            imap_connection.save()
            return JsonResponse(
                serializers.ImapConnectionResponse.model_validate(
                    imap_connection
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(is_an_organization_member(), name="get")
@method_decorator(is_platform_admin(), name="post")
class OrganizationsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if request.user.is_superuser:
            organizations = Organization.objects.all()
        else:
            organizations_users = OrganizationUser.objects.select_related(
                "organization"
            ).filter(user_id=request.user.id)
            organizations = [ou.organization for ou in organizations_users]  # type: ignore[assignment]
        response_list = []
        for org in organizations:
            response_list.append(
                serializers.OrganizationResponse.model_validate(org).model_dump()
            )
        return JsonResponse({"organizations": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.CreateOrganizationRequest.model_validate(payload)
            organization = serializer.to_django_model()
            organization.save()
            # Add the creating user as an admin of the organization
            org_user = OrganizationUser(
                user_id=request.user.id, organization_id=organization.id, role="admin"
            )
            org_user.save()
            return JsonResponse(
                serializers.OrganizationResponse.model_validate(
                    organization
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(is_an_organization_member(), name="post")
class UpdateSessionView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateSessionRequest.model_validate(payload)
            organization_id = serializer.active_organization_id
        except ValidationError as e:
            return JsonResponse({"error": e.errors()}, status=400)

        if (
            not OrganizationUser.objects.filter(
                user_id=request.user.id, organization_id=organization_id
            ).exists()
            and not request.user.is_superuser
        ):
            return JsonResponse(
                {"error": "Not a valid organization for the user."}, status=409
            )
        request.session["active_organization_id"] = organization_id
        response_serializer = serializers.SessionInfo.populate_from_session(
            request.session
        )
        return JsonResponse(response_serializer.model_dump(), status=200)


class RootView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return JsonResponse({"message": "Email Learning API is running."}, status=200)
