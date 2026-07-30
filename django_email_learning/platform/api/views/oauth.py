import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.error_responses import log_and_conflict_response
from django_email_learning.models import (
    Course,
    Enrollment,
    EnrollmentStatus,
    ImapConnection,
)
from django_email_learning.oauth_integrations.models import Session
from django_email_learning.oauth_integrations.serializers import CreateSessionRequest
from django_email_learning.platform.api import serializers
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)

logger = logging.getLogger(__name__)


@method_decorator(accessible_for(roles={"admin"}), name="get")
class OauthSessionView(View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            session = Session.objects.get(session_id=kwargs["session_id"])
            return JsonResponse({"session_id": session.session_id, "state": session.state}, status=200)
        except Session.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)


@method_decorator(accessible_for(roles={"admin"}), name="get")
class OauthGetGroupListView(View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        session = Session.objects.filter(session_id=kwargs["session_id"]).first()
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        handler_payload = jwt_service.decode_jwt(session.jwt_token)
        session_request = CreateSessionRequest(handler=handler_payload)
        handler = session_request.model_validate(obj=session_request).handler

        try:
            groups = handler.get_groups()
            if groups:
                results = [group.model_dump() for group in groups]
            else:
                results = None
            return JsonResponse({"groups": results}, status=200)
        except Exception as e:
            logger.error(f"Error retrieving groups for session {session.session_id}: {str(e)}")
            return JsonResponse({"error": "Failed to retrieve groups"}, status=500)


@method_decorator(accessible_for(roles={"admin"}), name="post")
class OauthGroupEnrollment(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        session = Session.objects.filter(session_id=kwargs["session_id"]).first()
        if not session:
            return JsonResponse({"error": "Session not found"}, status=404)

        payload = json.loads(request.body)

        try:
            serializer = serializers.GroupEnrollmentRequest.model_validate(payload)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        handler_payload = jwt_service.decode_jwt(session.jwt_token)
        session_request = CreateSessionRequest(handler=handler_payload)
        handler = session_request.model_validate(obj=session_request).handler

        try:
            users = handler.get_users_to_enroll(groups=serializer.groups)
            course = Course.objects.get(id=handler.course_id)
            for user in users:
                try:
                    EnrollCommand(
                        email=user.email,
                        course_slug=course.slug,
                        organization_id=course.organization_id,
                        no_verification=True,
                    ).execute()
                    enrollment = Enrollment.objects.get(
                        learner__email=user.email,
                        course_id=handler.course_id,
                        status=EnrollmentStatus.UNVERIFIED,
                    )
                    if user.photo_path:
                        learner = enrollment.learner
                        learner.photo = user.photo_path
                        learner.save(update_fields=["photo"])
                    VerifyEnrollmentCommand(
                        enrollment_id=enrollment.id,
                        verification_code=enrollment.activation_code,  # type: ignore[arg-type]
                    ).execute()
                except EnrollmentAlreadyExistsError:
                    logger.info(f"User {user.email} is already enrolled in course {handler.course_id}")
                except BlockedEmailError:
                    logger.warning(f"User {user.email} is blocked from enrolling in course {handler.course_id}")
                except LearnerCapExceededError:
                    logger.info(f"Organization {course.organization_id} learner cap reached; skipping {user.email}")
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to enroll user {user.email} for session {session.session_id}: {str(e)}")
            return JsonResponse({"message": "Enrollment process initiated"}, status=200)
        except Exception as e:
            logger.error(f"Error enrolling users for session {session.session_id}: {str(e)}")
            return JsonResponse({"error": "Failed to enroll users"}, status=500)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class ImapConnectionView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        response_list = []
        imap_connections = ImapConnection.objects.filter(organization_id=kwargs["organization_id"])
        for connection in imap_connections:
            response_list.append(serializers.ImapConnectionResponse.model_validate(connection).model_dump())
        return JsonResponse({"imap_connections": response_list}, status=200)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateImapConnectionRequest.model_validate(payload)
            imap_connection = serializer.to_django_model(organization_id=kwargs["organization_id"])
            imap_connection.save()
            return JsonResponse(
                serializers.ImapConnectionResponse.model_validate(imap_connection).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except Exception as e:
            # Connection/encryption failures here can carry hostnames and
            # credentials, so only the class name goes to the log.
            return log_and_conflict_response(logger, e, "Creating IMAP connection")
