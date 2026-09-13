"""How learners fared on each track of a branching course."""

from collections import defaultdict

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from django_email_learning.analytics import serializers
from django_email_learning.analytics.views import _content_delivery_qs, _course_ids, _json
from django_email_learning.decorators import is_an_organization_member
from django_email_learning.models import ContentTrack, Enrollment, EnrollmentStatus


@method_decorator(is_an_organization_member(), name="get")
class TrackBreakdownView(View):
    """Per-track outcomes for one course.

    A learner was routed onto a track once they were sent content on it, and finished it once
    they were sent content anywhere outside it or completed the course. Content on a track
    nested inside counts as the same track: branching again is still being on it.
    """

    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        organization_id = kwargs["organization_id"]
        course_ids = _course_ids(request)
        if len(course_ids) != 1:
            return JsonResponse({"error": "Pass exactly one course_id."}, status=400)
        course_id = course_ids[0]

        tracks = list(
            ContentTrack.objects.filter(course_id=course_id, course__organization_id=organization_id).order_by("id")
        )
        if not tracks:
            return _json(serializers.TrackBreakdownResponse(data=[]))
        parents = {track.id: track.parent_track_id for track in tracks}

        def within(track_id: int, candidate: int | None) -> bool:
            seen: set[int] = set()
            while candidate is not None and candidate not in seen:
                if candidate == track_id:
                    return True
                seen.add(candidate)
                candidate = parents.get(candidate)
            return False

        routes: dict[int, list[int | None]] = defaultdict(list)
        for enrollment_id, track_id in (
            _content_delivery_qs(organization_id, [course_id])
            .order_by("id")
            .values_list("enrollment_id", "course_content__track_id")
        ):
            routes[enrollment_id].append(track_id)
        statuses = dict(Enrollment.objects.filter(id__in=routes.keys()).values_list("id", "status"))

        rows = []
        for track in tracks:
            routed = finished = still_on_track = left_course = 0
            for enrollment_id, route in routes.items():
                entered_at = next((index for index, step in enumerate(route) if within(track.id, step)), None)
                if entered_at is None:
                    continue
                routed += 1
                moved_on = any(not within(track.id, step) for step in route[entered_at + 1 :])
                status = statuses.get(enrollment_id)
                if moved_on or status == EnrollmentStatus.COMPLETED:
                    finished += 1
                elif status == EnrollmentStatus.DEACTIVATED:
                    left_course += 1
                else:
                    still_on_track += 1
            rows.append(
                serializers.TrackBreakdownItem(
                    track_id=track.id,
                    name=track.name,
                    parent_track_id=track.parent_track_id,
                    routed=routed,
                    finished=finished,
                    still_on_track=still_on_track,
                    left_course=left_course,
                )
            )
        return _json(serializers.TrackBreakdownResponse(data=rows))
