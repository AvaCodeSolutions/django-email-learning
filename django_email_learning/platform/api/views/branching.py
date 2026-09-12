"""Authoring endpoints for course branching: tracks and the rules that route onto them.

Both resources are scoped to a course, and every lookup is filtered by the organization
in the URL so one organization cannot reach another's course by guessing an id.

Validation lives on the models - a track may only merge outward, a rule's condition has
to suit its source, a target may not rejoin at or before its branch point - so these
views translate `ValidationError` into a 400 rather than re-checking any of it.
"""

import json
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.models import ContentTrack, ContentTransition, Course, CourseContent
from django_email_learning.platform.api.serializers import branching as serializers


def _course_or_none(kwargs: dict) -> Any:
    return Course.objects.filter(id=kwargs["course_id"], organization_id=kwargs["organization_id"]).first()


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get")
class ContentTrackView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        course = _course_or_none(kwargs)
        if not course:
            return JsonResponse({"error": "Course not found"}, status=404)
        tracks = course.content_tracks.order_by("id")
        return JsonResponse(
            {"tracks": [serializers.ContentTrackResponse.model_validate(track).model_dump() for track in tracks]},
            status=200,
        )

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        course = _course_or_none(kwargs)
        if not course:
            return JsonResponse({"error": "Course not found"}, status=404)
        try:
            payload = serializers.CreateContentTrackRequest.model_validate(json.loads(request.body))
            track = ContentTrack(course=course, name=payload.name)
            if payload.parent_track_id is not None:
                parent = course.content_tracks.filter(id=payload.parent_track_id).first()
                if not parent:
                    return JsonResponse({"error": "Parent track not found"}, status=404)
                track.parent_track = parent
            if payload.merge_into_id is not None:
                merge_into = CourseContent.objects.filter(id=payload.merge_into_id, course=course).first()
                if not merge_into:
                    return JsonResponse({"error": "Merge point not found"}, status=404)
                track.merge_into = merge_into
            track.save()
            return JsonResponse(serializers.ContentTrackResponse.model_validate(track).model_dump(), status=201)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="delete")
@method_decorator(accessible_for(roles={"admin", "editor", "viewer", "instructor"}), name="get")
class ContentTransitionView(View):
    """The routing rules on one content."""

    def _content_or_none(self, kwargs: dict) -> Any:
        course = _course_or_none(kwargs)
        if not course:
            return None
        return CourseContent.objects.filter(id=kwargs["content_id"], course=course).first()

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        content = self._content_or_none(kwargs)
        if not content:
            return JsonResponse({"error": "Content not found"}, status=404)
        transitions = content.transitions.order_by("order")
        return JsonResponse(
            {
                "transitions": [
                    serializers.ContentTransitionResponse.model_validate(transition).model_dump()
                    for transition in transitions
                ]
            },
            status=200,
        )

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        content = self._content_or_none(kwargs)
        if not content:
            return JsonResponse({"error": "Content not found"}, status=404)
        try:
            payload = serializers.CreateContentTransitionRequest.model_validate(json.loads(request.body))
            target = ContentTrack.objects.filter(id=payload.target_id, course_id=content.course_id).first()
            if not target:
                return JsonResponse({"error": "Target track not found"}, status=404)
            transition = ContentTransition(
                source=content,
                order=payload.order,
                condition=payload.condition.value,
                threshold=payload.threshold,
                target=target,
            )
            transition.save()
            return JsonResponse(
                serializers.ContentTransitionResponse.model_validate(transition).model_dump(), status=201
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        content = self._content_or_none(kwargs)
        if not content:
            return JsonResponse({"error": "Content not found"}, status=404)
        transition = content.transitions.filter(id=kwargs["transition_id"]).first()
        if not transition:
            return JsonResponse({"error": "Transition not found"}, status=404)
        transition.delete()
        return JsonResponse({}, status=204)
