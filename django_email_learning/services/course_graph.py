"""One course's branching structure held in memory: its contents, tracks and routing rules.

Each of the three is read in a single query the first time something needs it, so walking a
track's ancestry, finding where a track rejoins or re-checking every rule in the course costs
a fixed number of queries however deeply its tracks nest. A graph is built from the database
by whatever request or job needs it and discarded with it - it reflects the rows as they were
when it read them, and nothing about it is shared between processes.

The rules on where a track may branch and rejoin live here too, because every one of them
compares against other rows of the same course.
"""

from collections import defaultdict
from typing import Iterable, Optional

from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from django_email_learning.models.course_contents import ContentTrack, ContentTransition, CourseContent


class CourseGraph:
    def __init__(
        self,
        course_id: int,
        contents: Optional[Iterable[CourseContent]] = None,
        tracks: Optional[Iterable[ContentTrack]] = None,
    ) -> None:
        self.course_id = course_id
        self._contents: Optional[dict[int, CourseContent]] = None
        self._published: dict[Optional[int], list[CourseContent]] = {}
        self._tracks: Optional[dict[int, ContentTrack]] = None
        self._rules: Optional[dict[int, list[ContentTransition]]] = None
        if contents is not None:
            self._set_contents(contents)
        if tracks is not None:
            self._tracks = {track.id: track for track in tracks}

    @classmethod
    def for_courses(cls, course_ids: set[int]) -> dict[int, "CourseGraph"]:
        """Graphs for any number of courses, their contents and tracks read in two queries."""
        contents: dict[int, list[CourseContent]] = defaultdict(list)
        for content in CourseContent.objects.filter(course_id__in=course_ids):
            contents[content.course_id].append(content)
        tracks: dict[int, list[ContentTrack]] = defaultdict(list)
        for track in ContentTrack.objects.filter(course_id__in=course_ids):
            tracks[track.course_id].append(track)
        return {course_id: cls(course_id, contents[course_id], tracks[course_id]) for course_id in course_ids}

    def _set_contents(self, contents: Iterable[CourseContent]) -> dict[int, CourseContent]:
        by_id = {content.id: content for content in contents}
        self._published = {}
        for content in sorted(by_id.values(), key=lambda c: c.priority):
            if content.is_published:
                self._published.setdefault(content.track_id, []).append(content)
        self._contents = by_id
        return by_id

    def _content_rows(self) -> dict[int, CourseContent]:
        if self._contents is None:
            return self._set_contents(CourseContent.objects.filter(course_id=self.course_id))
        return self._contents

    def _track_rows(self) -> dict[int, ContentTrack]:
        if self._tracks is None:
            self._tracks = {track.id: track for track in ContentTrack.objects.filter(course_id=self.course_id)}
        return self._tracks

    def _rule_rows(self) -> dict[int, list[ContentTransition]]:
        if self._rules is None:
            rules: dict[int, list[ContentTransition]] = defaultdict(list)
            for rule in ContentTransition.objects.filter(source__course_id=self.course_id).order_by(
                "source_id", "order"
            ):
                rules[rule.source_id].append(rule)
            self._rules = rules
        return self._rules

    def content(self, content_id: Optional[int]) -> Optional[CourseContent]:
        if content_id is None:
            return None
        return self._content_rows().get(content_id)

    def track(self, track_id: Optional[int]) -> Optional[ContentTrack]:
        """The track with this id, or None for the main spine or a track of another course."""
        if track_id is None:
            return None
        return self._track_rows().get(track_id)

    def published_on(self, track_id: Optional[int]) -> list[CourseContent]:
        """The published content on a track, or on the main spine for None, in priority order."""
        self._content_rows()
        return self._published.get(track_id, [])

    def rules_on(self, content_id: int) -> list[ContentTransition]:
        """The routing rules on a content, in the order they are evaluated."""
        return self._rule_rows().get(content_id, [])

    def ancestors(self, track: ContentTrack) -> list[ContentTrack]:
        """The tracks `track` branches off, innermost first.

        `track` is taken as given and its parents as stored, so a track being edited is placed
        against the rest of the course before it is saved.

        Stops when the chain repeats rather than at a fixed depth, so the result is the whole
        ancestry for valid data and still terminates on data that already holds a cycle.
        Bounding it by depth instead would silently truncate, which is what makes a
        depth-bounded cycle check miss any cycle longer than the bound.
        """
        chain: list[ContentTrack] = []
        seen: set[int] = set()
        parent = self.track(track.parent_track_id)
        while parent is not None and parent.id not in seen:
            seen.add(parent.id)
            chain.append(parent)
            parent = self.track(parent.parent_track_id)
        return chain

    def continuation(self, track: ContentTrack) -> Optional[CourseContent]:
        """Where a learner continues once `track` runs out, or None to end the course.

        A nested track without a merge point of its own defers to the track it branches off.
        """
        for candidate in [track, *self.ancestors(track)]:
            if candidate.merge_into_id:
                return self.content(candidate.merge_into_id)
        return None

    def check_track(self, track: ContentTrack) -> None:
        """Raise the first way `track` breaks the rules on where a track may branch and rejoin."""
        if track.parent_track_id is not None and self.track(track.parent_track_id) is None:
            raise ValidationError({"parent_track": "A parent track must belong to the same course."})
        merge_point = self.content(track.merge_into_id)
        if track.merge_into_id is not None and merge_point is None:
            raise ValidationError({"merge_into": "A merge point must belong to the same course."})
        ancestry = self.ancestors(track)
        if track.pk:
            if track.parent_track_id == track.pk:
                raise ValidationError({"parent_track": "A track cannot be its own parent."})
            if any(ancestor.pk == track.pk for ancestor in ancestry):
                raise ValidationError({"parent_track": "Track nesting cannot form a cycle."})
            if merge_point is not None and merge_point.track_id == track.pk:
                raise ValidationError({"merge_into": "A track cannot merge into its own content."})
        if merge_point is not None and merge_point.track_id is not None:
            # A merge may only move outward: onto the main spine, or onto a track this one
            # branches off. Nesting depth then strictly decreases every time a track runs
            # out, which is what makes the walk terminate by construction rather than by
            # the loop guard in content_sequence_service. A sibling or a nested track would
            # let two tracks hand a learner back and forth.
            if merge_point.track_id not in {ancestor.pk for ancestor in ancestry}:
                raise ValidationError(
                    {"merge_into": gettext("A track can only merge into the main spine or a track it branches off.")}
                )
        if len(ancestry) >= ContentTrack.MAX_NESTING_DEPTH:
            raise ValidationError(
                {
                    "parent_track": gettext("Tracks cannot be nested more than %(limit)d deep.")
                    % {"limit": ContentTrack.MAX_NESTING_DEPTH}
                }
            )

    def check_transition(self, transition: ContentTransition, source: CourseContent) -> None:
        """Raise the first way a rule on `source` points at a track it may not route onto.

        Routing a learner onto a track that rejoins ahead of where they branched is the whole
        point; one that rejoins behind it walks them into the same branch again, and again.
        That is only comparable when the merge lands on the source's own track - priorities
        are ordered within a track, not across them.
        """
        target = self.track(transition.target_id)
        if target is None:
            raise ValidationError({"target": "A target track must belong to the same course as the content."})
        if target.id == source.track_id:
            raise ValidationError({"target": "Content cannot route onto the track it is already on."})
        merge_point = self.continuation(target)
        if merge_point is None or merge_point.track_id != source.track_id:
            return
        if merge_point.priority <= source.priority:
            raise ValidationError(
                {
                    "target": gettext(
                        "'%(track)s' rejoins the course at or before this content, which would route "
                        "the learner onto it again."
                    )
                    % {"track": target.name}
                }
            )

    def validate(self) -> None:
        """Re-check every track and routing rule in the course as stored, raising the first violation."""
        for track in sorted(self._track_rows().values(), key=lambda t: t.id):
            self.check_track(track)
        for source_id, rules in sorted(self._rule_rows().items()):
            source = self.content(source_id)
            if source is None:
                continue
            for rule in rules:
                self.check_transition(rule, source)
