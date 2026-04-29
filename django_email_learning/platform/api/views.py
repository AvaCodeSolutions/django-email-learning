from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.utils import IntegrityError
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from datetime import timedelta, datetime
from urllib.parse import urlparse
from pydantic import ValidationError
from enum import StrEnum
from django_email_learning.oauth_integrations.models import Session
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.platform.api import serializers
from django_email_learning.platform.api.pagniated_api_mixin import PaginatedApiMixin
from django_email_learning.models import (
    ApiKey,
    Certificate,
    Course,
    CourseContent,
    Enrollment,
    EnrollmentStatus,
    ImapConnection,
    JobExecution,
    JobName,
    Learner,
    OrganizationUser,
    Organization,
)
from django_email_learning.decorators import (
    accessible_for,
    is_an_organization_member,
    is_platform_admin,
)
from django_email_learning.oauth_integrations.serializers import CreateSessionRequest
from django_email_learning.services import jwt_service
from typing import Any
import uuid
import json
import logging
import posixpath


logger = logging.getLogger(__name__)

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
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
                serializers.CourseResponse.from_django_model(
                    course, abs_url_builder=request.build_absolute_uri
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
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
        is_public = request.GET.get("is_public")
        if is_public is not None:
            if is_public.lower() in ["true", "yes"]:
                courses = courses.filter(is_public=True)
            elif is_public.lower() in ["false", "no"]:
                courses = courses.filter(is_public=False)

        response_list = []
        for course in courses:
            response_list.append(
                serializers.CourseResponse.from_django_model(
                    course, abs_url_builder=request.build_absolute_uri
                ).model_dump()
            )
        return JsonResponse({"courses": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(
    accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get"
)
class CourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseContentRequest.model_validate(payload)
            course = Course.objects.get(id=kwargs["course_id"])
            if serializer.priority is None:
                # Set priority to max existing priority + 1
                max_priority = (
                    CourseContent.objects.filter(course_id=course.id)
                    .aggregate(max_priority=models.Max("priority"))
                    .get("max_priority")
                )
                serializer.priority = (max_priority or 0) + 1
            course_content = serializer.to_django_model(course=course)

            return JsonResponse(
                serializers.CourseContentResponse.model_validate(
                    course_content
                ).model_dump(),
                status=201,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            course_contents = course.coursecontent_set.all().order_by("priority")
            response_list = []
            for content in course_contents:
                response_list.append(
                    serializers.CourseContentSummaryResponse.model_validate(
                        content
                    ).model_dump()
                )
            return JsonResponse({"course_contents": response_list}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class ReorderCourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.ReorderCourseContentsRequest.model_validate(
                payload
            )
            course = Course.objects.get(id=kwargs["course_id"])
            course_contents = {
                content.id: content for content in course.coursecontent_set.all()
            }

            with transaction.atomic():
                # Collect valid contents and set temporary negative priorities to avoid conflicts
                contents_to_update = []
                for index, content_id in enumerate(serializer.ordered_content_ids):
                    if content_id in course_contents:
                        content = course_contents[content_id]
                        content.priority = -(
                            index + 1
                        )  # Negative priority to avoid unique constraint conflicts
                        contents_to_update.append(content)

                # Bulk update with negative priorities first
                if contents_to_update:
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

                    # Now set the final positive priorities
                    for index, content in enumerate(contents_to_update):
                        content.priority = index + 1

                    # Final bulk update with correct priorities
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

            return JsonResponse(
                {"message": "Course contents reordered successfully"}, status=200
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor"}), name="delete"
)
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class SingleCourseContentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(id=kwargs["course_content_id"])
            return JsonResponse(
                serializers.CourseContentResponse.model_validate(
                    course_content
                ).model_dump(),
                status=200,
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(id=kwargs["course_content_id"])
            course_content.delete()
            return JsonResponse(
                {"message": "Course content deleted successfully"}, status=200
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.UpdateCourseContentRequest.model_validate(payload)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        try:
            return self._update_course_content_atomic(
                serializer, kwargs["course_content_id"]
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    @transaction.atomic
    def _update_course_content_atomic(
        self, serializer: serializers.UpdateCourseContentRequest, course_content_id: int
    ) -> JsonResponse:
        course_content = CourseContent.objects.get(id=course_content_id)

        if serializer.priority is not None:
            course_content.priority = serializer.priority
        if serializer.waiting_period is not None:
            course_content.waiting_period = serializer.waiting_period.to_seconds()

        if serializer.is_published is not None:
            course_content.is_published = serializer.is_published
            course_content.save()

        if serializer.lesson is not None and course_content.lesson is not None:
            lesson_serializer = serializer.lesson
            lesson = course_content.lesson
            if lesson_serializer.title is not None:
                lesson.title = lesson_serializer.title
            if lesson_serializer.content is not None:
                lesson.content = lesson_serializer.content
            lesson.save()

        if serializer.quiz is not None and course_content.quiz is not None:
            quiz_serializer = serializer.quiz
            quiz = course_content.quiz
            if quiz_serializer.title is not None:
                quiz.title = quiz_serializer.title
            if quiz_serializer.required_score is not None:
                quiz.required_score = quiz_serializer.required_score
            if quiz_serializer.selection_strategy is not None:
                quiz.selection_strategy = quiz_serializer.selection_strategy.value
            if quiz_serializer.deadline_days is not None:
                quiz.deadline_days = quiz_serializer.deadline_days
            if quiz_serializer.limited_attempts is not None:
                quiz.limited_attempts = quiz_serializer.limited_attempts
            if quiz_serializer.is_blocking is not None:
                quiz.is_blocking = quiz_serializer.is_blocking
            if "reminder_interval_days" in quiz_serializer.model_fields_set:
                quiz.reminder_interval_days = (
                    quiz_serializer.reminder_interval_days or 0
                )
            if quiz_serializer.questions is not None:
                question_ids = set()
                for question_data in quiz_serializer.questions:
                    if question_data.id:
                        question = quiz.questions.get(id=question_data.id)
                        question.text = question_data.text
                        question.priority = question_data.priority
                        question.save()
                    else:
                        question = quiz.questions.create(
                            text=question_data.text, priority=question_data.priority
                        )
                    question_ids.add(question.id)
                    answer_ids = set()
                    for answer_data in question_data.answers:
                        if answer_data.id:
                            answer = question.answers.get(id=answer_data.id)
                            answer.text = answer_data.text
                            answer.is_correct = answer_data.is_correct
                            answer.save()
                        else:
                            answer = question.answers.create(
                                text=answer_data.text, is_correct=answer_data.is_correct
                            )
                        answer_ids.add(answer.id)
                    question.answers.exclude(
                        id__in=answer_ids
                    ).delete()  # Remove any answers that were not included in the update payload
                quiz.questions.exclude(
                    id__in=question_ids
                ).delete()  # Remove any questions that were not included in the update payload
            quiz.save()

        course_content.save()
        return JsonResponse(
            serializers.CourseContentResponse.model_validate(
                course_content
            ).model_dump(),
            status=200,
        )


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor"}), name="delete"
)
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
class SingleCourseView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"])
            return JsonResponse(
                serializers.CourseResponse.from_django_model(
                    course, abs_url_builder=request.build_absolute_uri
                ).model_dump(),
                status=200,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.UpdateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(course_id=kwargs["course_id"])
            course.save()
            return JsonResponse(
                serializers.CourseResponse.from_django_model(
                    course, abs_url_builder=request.build_absolute_uri
                ).model_dump(),
                status=200,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
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
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin"}), name="get")
class OauthSessionView(View):
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            session = Session.objects.get(session_id=kwargs["session_id"])
            return JsonResponse(
                {"session_id": session.session_id, "state": session.state}, status=200
            )
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
            logger.error(
                f"Error retrieving groups for session {session.session_id}: {str(e)}"
            )
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
            for user in users:
                try:
                    EnrollCommand(
                        email=user.email,
                        course_slug=Course.objects.get(id=handler.course_id).slug,
                        organization_id=Course.objects.get(
                            id=handler.course_id
                        ).organization_id,
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
                    logger.info(
                        f"User {user.email} is already enrolled in course {handler.course_id}"
                    )
                except BlockedEmailError:
                    logger.warning(
                        f"User {user.email} is blocked from enrolling in course {handler.course_id}"
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(
                        f"Failed to enroll user {user.email} for session {session.session_id}: {str(e)}"
                    )
            return JsonResponse({"message": "Enrollment process initiated"}, status=200)
        except Exception as e:
            logger.error(
                f"Error enrolling users for session {session.session_id}: {str(e)}"
            )
            return JsonResponse({"error": "Failed to enroll users"}, status=500)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
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
            return JsonResponse({"error": e.json()}, status=400)
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
                serializers.OrganizationResponse.from_django_model(
                    org, request.build_absolute_uri
                ).model_dump()
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
            )
            org_user.save()
            return JsonResponse(
                serializers.OrganizationUserResponse.from_django_model(
                    org_user
                ).model_dump(),
                status=201,
            )
        except Organization.DoesNotExist:
            return JsonResponse({"error": "Organization not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_users = OrganizationUser.objects.filter(
            organization_id=kwargs["organization_id"]
        )
        response_list = []
        for org_user in organization_users:
            response_list.append(
                serializers.OrganizationUserResponse.from_django_model(
                    org_user
                ).model_dump()
            )
        return JsonResponse({"organization_users": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin"}), name="delete")
class SingleOrganizationUserView(View):
    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            org_user = OrganizationUser.objects.get(id=kwargs["user_id"])
            org_user.delete()
            return JsonResponse(
                {"message": "Organization user removed successfully"}, status=200
            )
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"error": "Organization user not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateOrganizationUserRoleRequest.model_validate(
                payload
            )
            org_user = OrganizationUser.objects.get(
                organization_id=kwargs["organization_id"], user_id=kwargs["user_id"]
            )
            org_user.role = serializer.role
            org_user.save()
            return JsonResponse(
                serializers.OrganizationUserResponse.from_django_model(
                    org_user
                ).model_dump(),
                status=200,
            )
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"error": "Organization user not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(is_platform_admin(), name="post")
@method_decorator(is_platform_admin(), name="delete")
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
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
            return JsonResponse(
                {"message": "Organization deleted successfully"}, status=200
            )
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
                user = User.objects.create_user(
                    username=email, email=email, password=uuid.uuid4().hex
                )
                form = PasswordResetForm(data={"email": email})
                if form.is_valid():
                    form.save(
                        request=request,
                        use_https=request.is_secure(),
                        from_email=DJANGO_EMAIL_LEARNING_SETTINGS.get(
                            "FROM_EMAIL", settings.DEFAULT_FROM_EMAIL
                        ),
                        email_template_name="emails/password_reset.txt",
                        html_email_template_name="emails/password_reset.html",
                        extra_email_context={
                            "organization": Organization.objects.get(
                                id=organization_id
                            ).name
                        },
                    )
                else:
                    raise ValueError(
                        "Failed to send password reset email to the new user."
                    )
            return JsonResponse(
                serializers.UserResponse.model_validate(user).model_dump(), status=200
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class SendLessonToPlatformUser(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if not request.user.email:
            return JsonResponse(
                {"error": "User does not have an email address"}, status=400
            )
        payload = json.loads(request.body)
        serializer = serializers.Identifier.model_validate(payload)
        email = request.user.email
        try:
            # Accept course content id directly (used by platform content table),
            # with a lesson-id fallback for backward compatibility.
            course_content = CourseContent.objects.filter(
                id=serializer.id,
                type="lesson",
                course__organization_id=kwargs["organization_id"],
            ).first()
            if course_content is None:
                course_content = CourseContent.objects.get(
                    lesson_id=serializer.id,
                    course__organization_id=kwargs["organization_id"],
                )
            SendLessonCommand(content_id=course_content.id, email=email).execute()
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Lesson not found"}, status=404)
        return JsonResponse(
            {"message": "Email content logged successfully"}, status=200
        )


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor"}), name="delete"
)
class FileView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # check file extension
        allowed_extensions = ["png", "jpg", "jpeg", "svg"]
        file_extension = uploaded_file.name.split(".")[-1].lower()
        if file_extension not in allowed_extensions:
            return JsonResponse({"error": "Invalid file type"}, status=400)

        date_prefix = timezone.now().strftime("%Y%m%d")

        file_path = default_storage.save(
            f"uploads/{date_prefix}/{kwargs['organization_id']}/{uploaded_file.name}",
            uploaded_file,
        )
        file_url = default_storage.url(file_path)
        return JsonResponse({"file_url": file_url, "file_path": file_path}, status=201)

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid request body"}, status=400)

        file_path = payload.get("file_path")
        file_url = payload.get("file_url")

        if not file_path and file_url:
            parsed_url_path = urlparse(file_url).path
            media_url = settings.MEDIA_URL or "/media/"
            normalized_media_url = (
                media_url if media_url.endswith("/") else f"{media_url}/"
            )
            if parsed_url_path.startswith(normalized_media_url):
                file_path = parsed_url_path[len(normalized_media_url) :]

        if not file_path:
            return JsonResponse({"error": "file_path is required"}, status=400)

        normalized_file_path = posixpath.normpath(str(file_path)).lstrip("/")
        path_parts = normalized_file_path.split("/")
        organization_id = str(kwargs["organization_id"])

        if (
            len(path_parts) < 4
            or path_parts[0] != "uploads"
            or path_parts[2] != organization_id
            or ".." in path_parts
        ):
            return JsonResponse({"error": "Invalid file path"}, status=400)

        if not default_storage.exists(normalized_file_path):
            return JsonResponse({"error": "File not found"}, status=404)

        default_storage.delete(normalized_file_path)
        return JsonResponse({"message": "File deleted successfully"}, status=200)


@method_decorator(is_an_organization_member(), name="post")
class UpdateSessionView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = json.loads(request.body)
            serializer = serializers.UpdateSessionRequest.model_validate(payload)
            organization_id = serializer.active_organization_id
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

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


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="get")
class LearnersView(PaginatedApiMixin, View):
    def get_query_set(self, request: Any) -> models.QuerySet:
        organization_id = self.kwargs["organization_id"]
        qs = Enrollment.objects.filter(course__organization_id=organization_id)
        if "course_id" in request.GET:
            course_id = request.GET["course_id"]
            qs = qs.filter(course_id=course_id)
        if "is_active" in request.GET:
            is_active_str = request.GET["is_active"].lower()
            if is_active_str in ["true", "yes"]:
                qs = qs.filter(status=EnrollmentStatus.ACTIVE)
        if "search" in request.GET:
            search_term = request.GET["search"]
            qs = qs.filter(models.Q(learner__email__icontains=search_term))
        learner_ids = qs.values("learner_id").distinct()
        return Learner.objects.filter(id__in=learner_ids)

    def get_item_serializer_class(self) -> Any:
        return serializers.LearnerResponse


@method_decorator(
    accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get"
)
class SingleLearnerView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            learner = Learner.objects.get(id=kwargs["learner_id"])
            enrollments = Enrollment.objects.filter(learner=learner)
            enroolments_list = []
            for enrollment in enrollments:
                certificate = Certificate.objects.filter(enrollment=enrollment).first()
                certificate_url = None
                if certificate:
                    certificate_url = request.build_absolute_uri(
                        reverse(
                            "django_email_learning:personalised:certificate",
                            kwargs={
                                "certificate_number": certificate.certificate_number
                            },
                        )
                    )
                enroolments_list.append(
                    serializers.EnrollmentSummaryResponse(
                        id=enrollment.id,
                        course_title=enrollment.course.title,
                        status=EnrollmentStatus(enrollment.status),
                        progress=enrollment.progress_percentage,
                        certificate_url=certificate_url,
                    )
                )
            return JsonResponse(
                serializers.LearnerDetailResponse(
                    id=learner.id, email=learner.email, enrollments=enroolments_list
                ).model_dump(),
                status=200,
            )
        except Learner.DoesNotExist:
            return JsonResponse({"error": "Learner not found"}, status=404)
        except ValidationError as e:
            logger.error(f"Error in SingleLearnerView: {e.json()}")
            return JsonResponse({"error": "An internal error occurred."}, status=500)


@method_decorator(accessible_for(roles={"admin", "instructor"}), name="post")
class EnrollmentsView(PaginatedApiMixin, View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateEnrollmentRequest.model_validate(payload)
            try:
                course = Course.objects.get(
                    id=kwargs["course_id"], organization_id=kwargs["organization_id"]
                )
            except Course.DoesNotExist:
                return JsonResponse({"error": "Course not found"}, status=404)
            command = EnrollCommand(
                email=serializer.learner_email,
                course_slug=course.slug,
                organization_id=kwargs["organization_id"],
                no_verification=True,  # skip verification email for manual enrollments through the API
            )
            try:
                command.execute()
            except BlockedEmailError as e:
                return JsonResponse({"error": str(e)}, status=403)
            except EnrollmentAlreadyExistsError as e:
                return JsonResponse({"error": str(e)}, status=409)

            enrollment = Enrollment.objects.get(
                learner__email=serializer.learner_email, course_id=kwargs["course_id"]
            )
            verify_command = VerifyEnrollmentCommand(
                enrollment_id=enrollment.id,
                verification_code=enrollment.activation_code,  # type: ignore[arg-type]
            )
            verify_command.execute()
            enrollment.refresh_from_db()
            return JsonResponse(
                serializers.EnrollmentResponse.from_django_model(
                    enrollment
                ).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
class EnrollmentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            enrollment = Enrollment.objects.get(id=kwargs["enrollment_id"])
            return JsonResponse(
                serializers.EnrollmentResponse.from_django_model(
                    enrollment
                ).model_dump(),
                status=200,
            )
        except Enrollment.DoesNotExist:
            return JsonResponse({"error": "Enrollment not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)


@method_decorator(
    accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get"
)
class EnrollmentsStatisticsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        course_id = kwargs["course_id"]
        a_week_ago = timezone.now() - timedelta(days=7)
        enrollments = (
            Enrollment.objects.filter(course_id=course_id, enrolled_at__gte=a_week_ago)
            .annotate(created_date=TruncDate("enrolled_at"))
            .values(
                "created_date",
            )
            .annotate(count=Count("id"))
            .order_by("created_date")
        )
        dates = [a_week_ago.date() + timedelta(days=i) for i in range(8)]
        enrollments_dict = {
            enrollment["created_date"]: enrollment["count"]
            for enrollment in enrollments
        }
        stats = [
            {"date": date.isoformat(), "count": enrollments_dict.get(date, 0)}
            for date in dates
        ]
        return JsonResponse({"statistics": stats}, status=200)


@method_decorator(is_platform_admin(), name="post")
@method_decorator(is_platform_admin(), name="get")
class ApiKeyView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            key = ApiKey.generate_key()
            api_key = ApiKey(key=key, created_by=request.user)
            api_key.save()
            return JsonResponse(
                serializers.ApiKeyResponse.from_django_model(api_key).model_dump(),
                status=201,
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        api_keys = ApiKey.objects.all()  # type: ignore[attr-defined]
        response_list = []
        for api_key in api_keys:
            response_list.append(
                serializers.ApiKeyResponse.from_django_model(api_key).model_dump()
            )
        return JsonResponse({"api_keys": response_list}, status=200)


@method_decorator(is_platform_admin(), name="delete")
class SingleApiKeyView(View):
    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            api_key = ApiKey.objects.get(id=kwargs["api_key_id"])
            api_key.delete()
            return JsonResponse({"message": "API Key deleted successfully"}, status=200)
        except ApiKey.DoesNotExist:
            return JsonResponse({"error": "API Key not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except IntegrityError as e:
            return JsonResponse({"error": str(e)}, status=409)


class JobHealthStatus(StrEnum):
    SUCCESS = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


DEFAULT_SUCCESS_THRESHOLD_MINUTES = 15
DEFAULT_WARNING_THRESHOLD_MINUTES = 45


@method_decorator(is_an_organization_member(), name="get")
class JobsStatus(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        jobs_status = {}
        for job in JobName:
            last_execution = (
                JobExecution.objects.filter(job_name=job.value)
                .order_by("-started_at")
                .first()
            )
            jobs_status[job.value] = {
                "job_name": job.value,
                "last_execution_status": last_execution.status
                if last_execution
                else None,
                "last_execution_started_at": last_execution.started_at.isoformat()
                if last_execution
                else None,
                "last_execution_finished_at": last_execution.finished_at.isoformat()
                if last_execution and last_execution.finished_at
                else None,
                "job_health_status": self.calculate_job_health_status(
                    last_execution.started_at
                )
                if last_execution
                else JobHealthStatus.CRITICAL.value,
            }

        return JsonResponse({"jobs": jobs_status}, status=200)

    @staticmethod
    def calculate_job_health_status(last_execution_started_at: datetime) -> str:
        success_threshold = DJANGO_EMAIL_LEARNING_SETTINGS.get(
            "JOB_HEALTH_SUCCESS_THRESHOLD_MINUTES", DEFAULT_SUCCESS_THRESHOLD_MINUTES
        )
        warning_threshold = DJANGO_EMAIL_LEARNING_SETTINGS.get(
            "JOB_HEALTH_WARNING_THRESHOLD_MINUTES", DEFAULT_WARNING_THRESHOLD_MINUTES
        )
        if not isinstance(success_threshold, int) or success_threshold <= 0:
            success_threshold = DEFAULT_SUCCESS_THRESHOLD_MINUTES
        if not isinstance(warning_threshold, int) or warning_threshold <= 0:
            warning_threshold = DEFAULT_WARNING_THRESHOLD_MINUTES
        if warning_threshold <= success_threshold:
            warning_threshold = (
                success_threshold + 30
            )  # Ensure warning threshold is greater than success threshold
        now = timezone.now()
        time_diff = now - last_execution_started_at
        minutes_diff = time_diff.total_seconds() / 60
        if minutes_diff <= success_threshold:
            return JobHealthStatus.SUCCESS.value
        elif minutes_diff <= warning_threshold:
            return JobHealthStatus.WARNING.value
        else:
            return JobHealthStatus.CRITICAL.value


class RootView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return JsonResponse({"message": "Email Learning API is running."}, status=200)
