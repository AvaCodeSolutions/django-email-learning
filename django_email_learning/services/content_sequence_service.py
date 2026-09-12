"""Which content comes next in a course, and which one comes first.

A course is an ordered list: every `CourseContent` carries a `priority` unique within
its course, and a learner walks them in ascending order, skipping anything unpublished.

A course may also carry `ContentTrack`s - named branches whose content is ordered among
itself rather than against the main spine. The walk stays inside the track it is already
on; when that runs out it continues at the track's `merge_into`, climbing `parent_track`
for the first merge point a nested track offers. A course with no tracks is the plain
ordered list above, which is every course today.

Both functions answer *which content* - creating the delivery and its schedule is the
caller's job.
"""

from typing import Optional

from django_email_learning.models.course_contents import ContentTrack, CourseContent
from django_email_learning.models.courses import Course


def first_content(course: Course) -> Optional[CourseContent]:
    """The content a new enrollment starts on, or None if the course has none published.

    Always on the main spine: a learner reaches a track by being routed onto it, never
    by starting there.
    """
    return (
        CourseContent.objects.filter(course=course, track__isnull=True, is_published=True).order_by("priority").first()
    )


def next_content(current: CourseContent) -> Optional[CourseContent]:
    """The content that follows `current`, or None if the course ends there.

    `current` itself does not have to be published: callers use this to step over content
    that was unpublished mid-course.
    """
    content = current
    visited_merge_points: set[int] = set()

    while True:
        following = (
            CourseContent.objects.filter(
                course_id=content.course_id,
                track_id=content.track_id,
                is_published=True,
                priority__gt=content.priority,
            )
            .order_by("priority")
            .first()
        )
        if following:
            return following

        merge_point = _merge_point_for(content.track)
        if merge_point is None:
            return None
        if merge_point.id in visited_merge_points:
            # Only reachable from a malformed graph, where merge points lead back to a
            # track already left. Ending the course beats looping forever.
            return None
        visited_merge_points.add(merge_point.id)
        if merge_point.is_published:
            return merge_point
        content = merge_point


def _merge_point_for(track: Optional[ContentTrack]) -> Optional[CourseContent]:
    """Where a learner continues after `track` runs out, or None if the course ends.

    A nested track without its own merge point defers to the track it branches off.
    """
    if track is None:
        return None
    for candidate in [track, *track.ancestors()]:
        if candidate.merge_into_id:
            return candidate.merge_into
    return None
