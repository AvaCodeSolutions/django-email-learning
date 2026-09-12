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


class CoursePath:
    """One course's shape, loaded once, for counting what is still ahead of a learner.

    `next_content()` answers one step at a time and queries as it goes, which is right for
    delivering but wrong for asking "how much of this is left" about a page full of
    enrollments. This holds the same rules in memory so the walk costs no queries at all.

    The projection assumes the learner does not branch again: it follows the track they
    are on and the merge points beyond it, and steps through a branch point the way an
    unrouted learner would. So the count changes when they *are* routed again, which is
    the point - their path really did get longer or shorter.
    """

    def __init__(self, contents: list[CourseContent], tracks: list[ContentTrack]) -> None:
        self._tracks = {track.id: track for track in tracks}
        self._published_by_track: dict[Optional[int], list[CourseContent]] = {}
        for content in sorted(contents, key=lambda c: c.priority):
            if content.is_published:
                self._published_by_track.setdefault(content.track_id, []).append(content)
        self._by_id = {content.id: content for content in contents}

    @classmethod
    def for_courses(cls, course_ids: set[int]) -> dict[int, "CoursePath"]:
        """Two queries for any number of courses."""
        contents = list(CourseContent.objects.filter(course_id__in=course_ids))
        tracks = list(ContentTrack.objects.filter(course_id__in=course_ids))
        return {
            course_id: cls(
                [content for content in contents if content.course_id == course_id],
                [track for track in tracks if track.course_id == course_id],
            )
            for course_id in course_ids
        }

    def content(self, content_id: int) -> Optional[CourseContent]:
        return self._by_id.get(content_id)

    def first(self) -> Optional[CourseContent]:
        spine = self._published_by_track.get(None, [])
        return spine[0] if spine else None

    def _continuation(self, track_id: Optional[int]) -> Optional[CourseContent]:
        while track_id is not None:
            track = self._tracks.get(track_id)
            if track is None:
                return None
            if track.merge_into_id:
                return self._by_id.get(track.merge_into_id)
            track_id = track.parent_track_id
        return None

    def remaining_after(self, content: CourseContent) -> int:
        """How many published contents a learner standing on `content` has still to come."""
        remaining = 0
        visited_merge_points: set[int] = set()
        while True:
            following = next(
                (
                    candidate
                    for candidate in self._published_by_track.get(content.track_id, [])
                    if candidate.priority > content.priority
                ),
                None,
            )
            if following:
                remaining += 1
                content = following
                continue

            merge_point = self._continuation(content.track_id)
            if merge_point is None or merge_point.id in visited_merge_points:
                return remaining
            visited_merge_points.add(merge_point.id)
            if merge_point.is_published:
                remaining += 1
            content = merge_point
