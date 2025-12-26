from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.utils import IntegrityError
from django.http import JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction

from pydantic import ValidationError

from django_email_learning.api import serializers
from django_email_learning.models import (
    Course,
    CourseContent,
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

        response_list = []
        for course in courses:
            response_list.append(
                serializers.CourseResponse.model_validate(course).model_dump()
            )
        return JsonResponse({"courses": response_list}, status=200)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
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


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
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


@method_decorator(accessible_for(roles={"admin", "editor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
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
            if course_content.type == "lesson" and course_content.lesson is not None:
                lesson = course_content.lesson
                lesson.is_published = serializer.is_published
                lesson.save()
            elif course_content.type == "quiz" and course_content.quiz is not None:
                quiz = course_content.quiz
                quiz.is_published = serializer.is_published
                quiz.save()

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
            if quiz_serializer.questions is not None:
                # Clear existing questions and answers
                quiz.questions.all().delete()
                for question_data in quiz_serializer.questions:
                    question = quiz.questions.create(
                        text=question_data.text, priority=question_data.priority
                    )
                    for answer_data in question_data.answers:
                        question.answers.create(
                            text=answer_data.text, is_correct=answer_data.is_correct
                        )
            quiz.save()

        course_content.save()
        return JsonResponse(
            serializers.CourseContentResponse.model_validate(
                course_content
            ).model_dump(),
            status=200,
        )


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
                serializers.CourseResponse.model_validate(course).model_dump(),
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
            return JsonResponse({"error": e.json()}, status=400)
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


class RootView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return JsonResponse({"message": "Email Learning API is running."}, status=200)
