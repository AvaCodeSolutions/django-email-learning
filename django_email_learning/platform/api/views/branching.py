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
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for
from django_email_learning.models import (
    ContentTrack,
    ContentTransition,
    Course,
    CourseContent,
    DecisionOption,
    TransitionCondition,
)
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
class ContentTrackDetailView(View):
    def _track_or_none(self, kwargs: dict) -> Any:
        course = _course_or_none(kwargs)
        if not course:
            return None
        return course.content_tracks.filter(id=kwargs["track_id"]).first()

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        track = self._track_or_none(kwargs)
        if not track:
            return JsonResponse({"error": "Track not found"}, status=404)
        try:
            payload = serializers.UpdateContentTrackRequest.model_validate(json.loads(request.body))
            with transaction.atomic():
                if payload.name is not None:
                    track.name = payload.name
                if "parent_track_id" in payload.model_fields_set:
                    if payload.parent_track_id is None:
                        track.parent_track = None
                    else:
                        parent = track.course.content_tracks.filter(id=payload.parent_track_id).first()
                        if not parent:
                            return JsonResponse({"error": "Parent track not found"}, status=404)
                        track.parent_track = parent
                if "merge_into_id" in payload.model_fields_set:
                    if payload.merge_into_id is None:
                        track.merge_into = None
                    else:
                        merge_into = CourseContent.objects.filter(
                            id=payload.merge_into_id, course_id=track.course_id
                        ).first()
                        if not merge_into:
                            return JsonResponse({"error": "Merge point not found"}, status=404)
                        track.merge_into = merge_into
                track.save()
                # Moving a merge point can put it behind a rule's branch point, which only
                # the rule's own check sees.
                track.course.validate_branching()
            return JsonResponse(serializers.ContentTrackResponse.model_validate(track).model_dump(), status=200)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        track = self._track_or_none(kwargs)
        if not track:
            return JsonResponse({"error": "Track not found"}, status=404)
        try:
            track.delete()
        except DjangoValidationError as e:
            # ContentTrack.delete() refuses while the track still holds content.
            return JsonResponse({"error": "; ".join(e.messages)}, status=409)
        return JsonResponse({}, status=204)


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
@method_decorator(accessible_for(roles={"admin", "editor"}), name="put")
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
        transitions = content.transitions.select_related("option").order_by("order")
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
            option = None
            if payload.option_id is not None:
                option = DecisionOption.objects.filter(id=payload.option_id, decision_id=content.decision_id).first()
                if not option:
                    return JsonResponse({"error": "Answer not found"}, status=404)
            transition = ContentTransition(
                source=content,
                order=payload.order,
                condition=payload.condition.value,
                threshold=payload.threshold,
                target=target,
                option=option,
            )
            transition.save()
            return JsonResponse(
                serializers.ContentTransitionResponse.model_validate(transition).model_dump(), status=201
            )
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)

    def put(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        """Replace the whole rule set, so the order can be edited freely and saved at once."""
        content = self._content_or_none(kwargs)
        if not content:
            return JsonResponse({"error": "Content not found"}, status=404)
        try:
            payload = serializers.ReplaceContentTransitionsRequest.model_validate(json.loads(request.body))
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        rules = payload.transitions
        if any(rule.condition == TransitionCondition.DEFAULT for rule in rules[:-1]):
            return JsonResponse(
                {"error": ["An 'otherwise' rule must come last: any rule after it could never match."]},
                status=400,
            )
        targets = {
            track.id: track
            for track in ContentTrack.objects.filter(
                course_id=content.course_id, id__in={rule.target_id for rule in rules}
            )
        }
        if any(rule.target_id not in targets for rule in rules):
            return JsonResponse({"error": "Target track not found"}, status=404)
        wanted_options = {rule.option_id for rule in rules if rule.option_id is not None}
        options = {
            option.id: option
            for option in DecisionOption.objects.filter(decision_id=content.decision_id, id__in=wanted_options)
        }
        if len(options) != len(wanted_options):
            return JsonResponse({"error": "Answer not found"}, status=404)

        try:
            with transaction.atomic():
                content.transitions.all().delete()
                saved = []
                for order, rule in enumerate(rules, start=1):
                    transition = ContentTransition(
                        source=content,
                        order=order,
                        condition=rule.condition.value,
                        threshold=rule.threshold,
                        target=targets[rule.target_id],
                        option=options.get(rule.option_id) if rule.option_id is not None else None,
                    )
                    transition.save()
                    saved.append(transition)
        except DjangoValidationError as e:
            return JsonResponse({"error": e.messages}, status=400)
        return JsonResponse(
            {
                "transitions": [
                    serializers.ContentTransitionResponse.model_validate(transition).model_dump()
                    for transition in saved
                ]
            },
            status=200,
        )

    def delete(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        content = self._content_or_none(kwargs)
        if not content:
            return JsonResponse({"error": "Content not found"}, status=404)
        transition_id = kwargs.get("transition_id")
        if transition_id is None:
            return JsonResponse({"error": "Transition not found"}, status=404)
        transition = content.transitions.filter(id=transition_id).first()
        if not transition:
            return JsonResponse({"error": "Transition not found"}, status=404)
        transition.delete()
        return JsonResponse({}, status=204)
