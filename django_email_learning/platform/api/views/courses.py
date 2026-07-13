import json
import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from django.db.utils import IntegrityError
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.models import (
    Course,
    CourseContent,
    CourseContentType,
)
from django_email_learning.platform.api import serializers
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)

logger = logging.getLogger(__name__)


class CourseCreationMixin:
    """Provides the can_create_course hook shared by CourseView and SingleCourseView."""

    def can_create_course(self, request: HttpRequest, organization_id: int) -> bool:
        """
        Override to add custom course creation logic (e.g. plan limits, feature flags).
        Return False to reject the request with a 403 before any DB work happens.
        The result is also included in create and delete course responses so the
        client always knows the current state after a mutation.
        """
        return True


@method_decorator(ensure_csrf_cookie, name="get")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class CourseView(CourseCreationMixin, View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        if not self.can_create_course(request, organization_id):
            return JsonResponse({"error": "Course creation not allowed."}, status=403)
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseRequest.model_validate(payload)
            course = serializer.to_django_model(organization_id=organization_id)
            course.save()
            response_data = serializers.CourseResponse.from_django_model(
                course, abs_url_builder=request.build_absolute_uri
            ).model_dump()
            response_data["can_create_course"] = self.can_create_course(request, organization_id)
            return JsonResponse(response_data, status=201)
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
@method_decorator(accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get")
class CourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.CreateCourseContentRequest.model_validate(payload)
            course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
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
                serializers.CourseContentResponse.model_validate(course_content).model_dump(),
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
            course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
            course_contents = course.coursecontent_set.all().order_by("priority")
            response_list = []
            for content in course_contents:
                response_list.append(serializers.CourseContentSummaryResponse.model_validate(content).model_dump())
            return JsonResponse({"course_contents": response_list}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class ReorderCourseContentView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = serializers.ReorderCourseContentsRequest.model_validate(payload)
            course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
            course_contents = {content.id: content for content in course.coursecontent_set.all()}

            with transaction.atomic():
                # Collect valid contents and set temporary negative priorities to avoid conflicts
                contents_to_update = []
                for index, content_id in enumerate(serializer.ordered_content_ids):
                    if content_id in course_contents:
                        content = course_contents[content_id]
                        content.priority = -(index + 1)  # Negative priority to avoid unique constraint conflicts
                        contents_to_update.append(content)

                # Bulk update with negative priorities first
                if contents_to_update:
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

                    # Now set the final positive priorities
                    for index, content in enumerate(contents_to_update):
                        content.priority = index + 1

                    # Final bulk update with correct priorities
                    CourseContent.objects.bulk_update(contents_to_update, ["priority"])

            return JsonResponse({"message": "Course contents reordered successfully"}, status=200)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class SingleCourseContentView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(
                id=kwargs["course_content_id"],
                course_id=kwargs["course_id"],
                course__organization_id=kwargs["organization_id"],
            )
            return JsonResponse(
                serializers.CourseContentResponse.model_validate(course_content).model_dump(),
                status=200,
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

    def delete(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            course_content = CourseContent.objects.get(
                id=kwargs["course_content_id"],
                course_id=kwargs["course_id"],
                course__organization_id=kwargs["organization_id"],
            )
            course_content.delete()
            return JsonResponse({"message": "Course content deleted successfully"}, status=200)
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
                serializer, kwargs["course_content_id"], kwargs["course_id"], kwargs["organization_id"]
            )
        except CourseContent.DoesNotExist:
            return JsonResponse({"error": "Course content not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)

    @transaction.atomic
    def _update_course_content_atomic(
        self,
        serializer: serializers.UpdateCourseContentRequest,
        course_content_id: int,
        course_id: int,
        organization_id: int,
    ) -> JsonResponse:
        course_content = CourseContent.objects.get(
            id=course_content_id, course_id=course_id, course__organization_id=organization_id
        )

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

        if serializer.assignment is not None and course_content.assignment is not None:
            assignment_serializer = serializer.assignment
            assignment = course_content.assignment
            if assignment_serializer.title is not None:
                assignment.title = assignment_serializer.title
            if assignment_serializer.description is not None:
                assignment.description = assignment_serializer.description
            if assignment_serializer.deadline_days is not None:
                assignment.deadline_days = assignment_serializer.deadline_days
            if assignment_serializer.requires_text_submission is not None:
                assignment.requires_text_submission = assignment_serializer.requires_text_submission
            if assignment_serializer.requires_file_submission is not None:
                assignment.requires_file_submission = assignment_serializer.requires_file_submission
            if assignment_serializer.reminder_interval_days is not None:
                assignment.reminder_interval_days = assignment_serializer.reminder_interval_days
            assignment.save()

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
                quiz.reminder_interval_days = quiz_serializer.reminder_interval_days or 0
            if quiz_serializer.questions is not None:
                question_ids = set()
                for question_data in quiz_serializer.questions:
                    if question_data.id:
                        question = quiz.questions.get(id=question_data.id)
                        question.text = question_data.text
                        question.priority = question_data.priority
                        question.save()
                    else:
                        question = quiz.questions.create(text=question_data.text, priority=question_data.priority)
                    question_ids.add(question.id)
                    answer_ids = set()
                    for answer_data in question_data.answers:
                        if answer_data.id:
                            answer = question.answers.get(id=answer_data.id)
                            answer.text = answer_data.text
                            answer.is_correct = answer_data.is_correct
                            answer.save()
                        else:
                            answer = question.answers.create(text=answer_data.text, is_correct=answer_data.is_correct)
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
            serializers.CourseContentResponse.model_validate(course_content).model_dump(),
            status=200,
        )


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "instructor", "viewer"}), name="get")
class SingleCourseView(CourseCreationMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
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
            course = serializer.to_django_model(
                course_id=kwargs["course_id"], organization_id=kwargs["organization_id"]
            )
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
            course = Course.objects.get(id=kwargs["course_id"], organization_id=kwargs["organization_id"])
            organization_id = course.organization_id
            course.delete()
            return JsonResponse(
                {
                    "message": "Course deleted successfully",
                    "can_create_course": self.can_create_course(request, organization_id),
                },
                status=200,
            )
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except (IntegrityError, ValueError) as e:
            return JsonResponse({"error": str(e)}, status=409)


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class SendLessonToPlatformUser(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if not request.user.email:
            return JsonResponse({"error": "User does not have an email address"}, status=400)
        payload = json.loads(request.body)
        serializer = serializers.Identifier.model_validate(payload)
        email = request.user.email
        try:
            # Accept course content id directly (used by platform content table),
            # with a lesson-id fallback for backward compatibility.
            course_content = CourseContent.objects.filter(
                id=serializer.id,
                type=CourseContentType.LESSON,
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
        return JsonResponse({"message": "Email content logged successfully"}, status=200)
