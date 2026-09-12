"""Which content comes next in a course, and which one comes first.

A course is an ordered list: every `CourseContent` carries a `priority` unique within
its course, and a learner walks them in ascending order, skipping anything unpublished.

A course may also carry `ContentTrack`s - named branches whose content is ordered among
itself rather than against the main spine. The walk stays inside the track it is already
on; when that runs out it continues at the track's merge point, climbing `parent_track`
for the first one a nested track offers.

A learner reaches a track through a `ContentTransition`: content carrying routing rules
is a branch point, and the outcome it produced picks the track. Content with no rules is
walked in plain priority order, which is every course with no tracks - so a course that
does not branch behaves exactly as it always has.

Both functions answer *which content* - creating the delivery and its schedule is the
caller's job.
"""

from typing import Optional

from django_email_learning.models.course_contents import ContentTrack, CourseContent, QuizOutcome
from django_email_learning.models.courses import Course

# Told apart from a genuine `None`, which means "routed, and the route ends the course".
_NO_ROUTE = object()


def first_content(course: Course) -> Optional[CourseContent]:
    """The content a new enrollment starts on, or None if the course has none published.

    Always on the main spine: a learner reaches a track by being routed onto it, never
    by starting there.
    """
    return (
        CourseContent.objects.filter(course=course, track__isnull=True, is_published=True).order_by("priority").first()
    )


def next_content(current: CourseContent, outcome: Optional[QuizOutcome] = None) -> Optional[CourseContent]:
    """The content that follows `current`, or None if the course ends there.

    `outcome` is what `current` produced, and is what the routing rules on it are
    evaluated against. Without one - a lesson being delivered, a deadline passing, the
    inactivity job stepping an enrollment along - only the linear walk applies, so
    content that would have branched falls through to the next content in its track.

    `current` itself does not have to be published: callers use this to step over content
    that was unpublished mid-course.
    """
    if outcome is not None:
        routed = _route(current, outcome)
        if routed is not _NO_ROUTE:
            return routed  # type: ignore[return-value]
    return _walk_from(current)


def _route(source: CourseContent, outcome: QuizOutcome) -> object:
    """The content the routing rules on `source` select, or `_NO_ROUTE` if none apply."""
    transitions = list(source.transitions.select_related("target").order_by("order"))
    for transition in transitions:
        if transition.matches(outcome):
            return _enter(transition.target)
    return _NO_ROUTE


def _enter(track: ContentTrack) -> Optional[CourseContent]:
    """The first published content on `track`, or where it continues if it has none."""
    entry = CourseContent.objects.filter(track=track, is_published=True).order_by("priority").first()
    if entry:
        return entry
    merge_point = track.continuation()
    if merge_point is None:
        return None
    if merge_point.is_published:
        return merge_point
    return _walk_from(merge_point)


def _walk_from(start: CourseContent) -> Optional[CourseContent]:
    """The next published content after `start`, following merge points outward."""
    content = start
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

        merge_point = content.track.continuation() if content.track else None
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
