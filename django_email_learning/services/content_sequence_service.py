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

The walk runs over a `CourseGraph`, so a step costs a fixed number of queries however
deeply the course's tracks nest. Every function here answers *which content* - creating
the delivery and its schedule is the caller's job.
"""

from typing import Optional

from django_email_learning.models.course_contents import ContentTrack, CourseContent, RoutingOutcome
from django_email_learning.models.courses import Course
from django_email_learning.services.course_graph import CourseGraph

# Told apart from a genuine `None`, which means "routed, and the route ends the course".
_NO_ROUTE = object()


def first_content(course: Course) -> Optional[CourseContent]:
    """The content a new enrollment starts on, or None if the course has none published.

    Always on the main spine: a learner reaches a track by being routed onto it, never
    by starting there.
    """
    return first_in(CourseGraph(course.id))


def first_in(graph: CourseGraph) -> Optional[CourseContent]:
    """`first_content()` for a course whose graph is already built."""
    spine = graph.published_on(None)
    return spine[0] if spine else None


def next_content(current: CourseContent, outcome: Optional[RoutingOutcome] = None) -> Optional[CourseContent]:
    """The content that follows `current`, or None if the course ends there.

    `outcome` is what `current` produced, and is what the routing rules on it are
    evaluated against. Without one - a lesson being delivered, a deadline passing, the
    inactivity job stepping an enrollment along - only the linear walk applies, so
    content that would have branched falls through to the next content in its track.

    `current` itself does not have to be published: callers use this to step over content
    that was unpublished mid-course.
    """
    graph = CourseGraph(current.course_id)
    if outcome is not None:
        routed = _route(graph, current, outcome)
        if routed is not _NO_ROUTE:
            return routed  # type: ignore[return-value]
    return _walk_from(graph, current)


def remaining_after(graph: CourseGraph, content: CourseContent) -> int:
    """How many published contents a learner standing on `content` has still to come.

    The projection assumes the learner does not branch again: it follows the track they
    are on and the merge points beyond it, and steps through a branch point the way an
    unrouted learner would. So the count changes when they *are* routed again, which is
    the point - their path really did get longer or shorter.
    """
    remaining = 0
    counted: set[int] = set()
    following = _walk_from(graph, content)
    # Content met a second time is only reachable from a malformed graph whose merge points
    # lead back to published content already counted.
    while following is not None and following.id not in counted:
        counted.add(following.id)
        remaining += 1
        following = _walk_from(graph, following)
    return remaining


def _route(graph: CourseGraph, source: CourseContent, outcome: RoutingOutcome) -> object:
    """The content the routing rules on `source` select, or `_NO_ROUTE` if none apply."""
    for rule in graph.rules_on(source.id):
        if rule.matches(outcome):
            target = graph.track(rule.target_id)
            if target is not None:
                return _enter(graph, target)
    return _NO_ROUTE


def _enter(graph: CourseGraph, track: ContentTrack) -> Optional[CourseContent]:
    """The first published content on `track`, or where it continues if it has none."""
    on_track = graph.published_on(track.id)
    if on_track:
        return on_track[0]
    merge_point = graph.continuation(track)
    if merge_point is None:
        return None
    if merge_point.is_published:
        return merge_point
    return _walk_from(graph, merge_point)


def _walk_from(graph: CourseGraph, start: CourseContent) -> Optional[CourseContent]:
    """The next published content after `start`, following merge points outward."""
    content = start
    visited_merge_points: set[int] = set()

    while True:
        following = next(
            (candidate for candidate in graph.published_on(content.track_id) if candidate.priority > content.priority),
            None,
        )
        if following:
            return following

        track = graph.track(content.track_id)
        merge_point = graph.continuation(track) if track else None
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
