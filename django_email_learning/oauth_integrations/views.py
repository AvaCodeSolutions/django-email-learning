import json

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils.translation import get_language, get_language_info
from django.utils.translation import gettext as _
from django.views import View
from pydantic import ValidationError

from django_email_learning.apps import PLATFORM_ADMIN_GROUP_NAME
from django_email_learning.models import Course, OrganizationUser
from django_email_learning.services.jwt_service import (
    InvalidTokenException,
    decode_jwt,
    generate_jwt,
)

from .models import Session, SessionState
from .serializers import CreateSessionRequest


def _command_result_response(  # type: ignore[no-untyped-def]
    request,
    *,
    page_title: str,
    success_message: str | None = None,
    error_message: str | None = None,
    status_code: int = 200,
) -> HttpResponse:
    current_lang_code = get_language()
    lang_info = get_language_info(current_lang_code)
    return render(
        request,
        "personalised/command_result.html",
        {
            "page_title": page_title,
            "appContext": {
                "successMessage": success_message,
                "errorMessage": error_message,
                "closeWindow": True,
                "direction": "rtl" if lang_info["bidi"] else "ltr",
                "localeMessages": {"Confirm": _("Confirm")},
            },
        },
        status=status_code,
    )


def _has_oauth_session_access(user, organization_id: int) -> bool:  # type: ignore[no-untyped-def]
    if user.is_superuser:
        return True
    if user.groups.filter(name=PLATFORM_ADMIN_GROUP_NAME).exists():
        return True
    return OrganizationUser.objects.filter(
        user=user,
        organization_id=organization_id,
        role="admin",
    ).exists()


class SessionsView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        payload = json.loads(request.body)

        try:
            serializer = CreateSessionRequest.model_validate(payload)
        except ValidationError as ve:
            return JsonResponse({"error": ve.errors()}, status=400)

        handler = serializer.handler

        if hasattr(handler, "course_id") and handler.course_id is not None:
            try:
                course = Course.objects.get(id=handler.course_id)
            except Course.DoesNotExist:
                return JsonResponse({"error": "Course not found"}, status=404)

            if not _has_oauth_session_access(request.user, course.organization_id):
                return JsonResponse({"error": "Forbidden"}, status=403)

        temp_session = Session.objects.create(jwt_token="pending")
        authorization_url = handler.get_authorization_url(temp_session.session_id)
        handler_payload = serializer.handler.model_dump(mode="json")
        temp_session.jwt_token = generate_jwt(handler_payload)
        temp_session.save(update_fields=["jwt_token"])

        return JsonResponse(
            {
                "session_id": temp_session.session_id,
                "authorization_url": authorization_url,
            },
            status=201,
        )


class RedirectView(View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        session_id = request.GET.get("state")
        code = request.GET.get("code")
        if not session_id:
            return _command_result_response(
                request,
                page_title=_("Authorization Error"),
                error_message=_("Missing state parameter."),
                status_code=400,
            )

        try:
            session = Session.objects.get(
                session_id=session_id, state=SessionState.PENDING
            )
        except Session.DoesNotExist:
            return _command_result_response(
                request,
                page_title=_("Authorization Error"),
                error_message=_("Invalid session identifier."),
                status_code=404,
            )

        if not code:
            session.state = SessionState.FAILED
            session.save(update_fields=["state"])
            return _command_result_response(
                request,
                page_title=_("Authorization Error"),
                error_message=_("Missing code parameter."),
                status_code=400,
            )

        try:
            session.state = SessionState.PROCESSING
            session.save(update_fields=["state"])

            decoded_request = decode_jwt(session.jwt_token)
            # command_payload = decoded_request.get("handler", {})
            decoded_request["code"] = code
            decoded_request["state"] = session_id
            session_request = CreateSessionRequest(handler=decoded_request)
            handler = session_request.model_validate(obj=session_request).handler
            access_token = handler.handle_redirect()
            session.access_token = generate_jwt({"access_token": access_token})
            session.state = SessionState.COMPLETED
            session.save(update_fields=["state", "access_token"])
            return _command_result_response(
                request,
                page_title=_("Authorization Complete"),
                success_message=_(
                    "Google authorization completed successfully. You can close this window."
                ),
                status_code=200,
            )
        except InvalidTokenException:
            session.state = SessionState.FAILED
            session.save(update_fields=["state"])
            return _command_result_response(
                request,
                page_title=_("Authorization Error"),
                error_message=_("Invalid OAuth session token."),
                status_code=400,
            )
        except Exception as e:  # noqa: BLE001
            print(f"Error processing OAuth redirect: {str(e)}")
            session.state = SessionState.FAILED
            session.save(update_fields=["state"])
            return _command_result_response(
                request,
                page_title=_("Authorization Error"),
                error_message=str(e),
                status_code=400,
            )
