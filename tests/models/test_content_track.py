import pytest
from django.core.exceptions import ValidationError

from django_email_learning.models import ContentTrack, Course, CourseContent, Lesson


@pytest.fixture
def spine_content(db, course, lesson) -> CourseContent:
    return CourseContent.objects.create(
        course=course,
        priority=1,
        type="lesson",
        lesson=lesson,
        waiting_period=3600,
        is_published=True,
    )


def make_content(course, priority, track=None, title="Extra"):
    lesson = Lesson.objects.create(title=title, content="...")
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=lesson,
        waiting_period=3600,
        is_published=True,
    )


def test_priorities_stay_unique_on_the_main_spine(db, course, spine_content):
    """The regression the split constraint guards: NULL tracks must not read as distinct."""
    with pytest.raises(ValidationError, match="unique_priority_per_course_spine"):
        make_content(course, priority=spine_content.priority, title="Clashing")


def test_priorities_stay_unique_within_one_track(db, course):
    track = ContentTrack.objects.create(course=course, name="Path")
    make_content(course, priority=1, track=track)

    with pytest.raises(ValidationError, match="unique_priority_per_track"):
        make_content(course, priority=1, track=track, title="Clashing")


def test_the_same_priority_is_free_on_a_different_track(db, course, spine_content):
    track = ContentTrack.objects.create(course=course, name="Path")
    other_track = ContentTrack.objects.create(course=course, name="Other path")

    on_track = make_content(course, priority=spine_content.priority, track=track)
    on_other = make_content(course, priority=spine_content.priority, track=other_track, title="Also")

    assert on_track.priority == on_other.priority == spine_content.priority


def test_track_names_are_unique_within_a_course(db, course):
    ContentTrack.objects.create(course=course, name="Path")

    with pytest.raises(ValidationError):
        ContentTrack.objects.create(course=course, name="Path")


def test_a_parent_track_must_belong_to_the_same_course(db, course, imap_connection):
    other_course = Course.objects.create(
        title="Other Course",
        slug="other-course",
        imap_connection=imap_connection,
        organization_id=1,
    )
    foreign_parent = ContentTrack.objects.create(course=other_course, name="Foreign")

    with pytest.raises(ValidationError, match="same course"):
        ContentTrack.objects.create(course=course, name="Path", parent_track=foreign_parent)


def test_a_merge_point_must_belong_to_the_same_course(db, course, imap_connection):
    other_course = Course.objects.create(
        title="Other Course",
        slug="other-course",
        imap_connection=imap_connection,
        organization_id=1,
    )
    foreign_content = make_content(other_course, priority=1, title="Foreign")

    with pytest.raises(ValidationError, match="same course"):
        ContentTrack.objects.create(course=course, name="Path", merge_into=foreign_content)


def test_a_track_cannot_be_its_own_parent(db, course):
    track = ContentTrack.objects.create(course=course, name="Path")
    track.parent_track = track

    with pytest.raises(ValidationError, match="its own parent"):
        track.save()


def test_track_nesting_cannot_form_a_cycle(db, course):
    outer = ContentTrack.objects.create(course=course, name="Outer")
    inner = ContentTrack.objects.create(course=course, name="Inner", parent_track=outer)
    outer.parent_track = inner

    with pytest.raises(ValidationError, match="cycle"):
        outer.save()


def test_a_track_cannot_merge_into_its_own_content(db, course):
    track = ContentTrack.objects.create(course=course, name="Path")
    own_content = make_content(course, priority=1, track=track)
    track.merge_into = own_content

    with pytest.raises(ValidationError, match="its own content"):
        track.save()


def test_ancestors_are_listed_innermost_first(db, course):
    outer = ContentTrack.objects.create(course=course, name="Outer")
    middle = ContentTrack.objects.create(course=course, name="Middle", parent_track=outer)
    inner = ContentTrack.objects.create(course=course, name="Inner", parent_track=middle)

    assert inner.ancestors() == [middle, outer]


def test_a_populated_track_cannot_be_deleted(db, course):
    track = ContentTrack.objects.create(course=course, name="Path")
    make_content(course, priority=1, track=track)

    with pytest.raises(ValidationError, match="still has content"):
        track.delete()


def test_an_empty_track_can_be_deleted(db, course):
    track = ContentTrack.objects.create(course=course, name="Path")

    track.delete()

    assert not ContentTrack.objects.filter(pk=track.pk).exists()


def test_deleting_a_course_takes_its_tracks_with_it(db, course):
    ContentTrack.objects.create(course=course, name="Path")

    course.delete()

    assert not ContentTrack.objects.exists()


def nest(course, depth, prefix="t"):
    """A chain of `depth` tracks, each the parent of the next. Returns the innermost."""
    track = ContentTrack.objects.create(course=course, name=f"{prefix}0")
    for level in range(1, depth):
        track = ContentTrack.objects.create(course=course, name=f"{prefix}{level}", parent_track=track)
    return track


def test_nesting_is_allowed_up_to_the_limit(db, course):
    innermost = nest(course, ContentTrack.MAX_NESTING_DEPTH)

    assert len(innermost.ancestors()) == ContentTrack.MAX_NESTING_DEPTH - 1


def test_nesting_past_the_limit_is_rejected(db, course):
    innermost = nest(course, ContentTrack.MAX_NESTING_DEPTH)

    with pytest.raises(ValidationError, match="nested more than"):
        ContentTrack.objects.create(course=course, name="one too many", parent_track=innermost)


def test_a_cycle_longer_than_the_nesting_limit_cannot_be_built(db, course):
    """The depth cap is what keeps a cycle from being assembled out of reach of the check.

    Before it existed, a chain could be nested past MAX_NESTING_DEPTH and then closed into
    a cycle: the check walked only as far as the cap, so it never met the repeated track.
    """
    with pytest.raises(ValidationError, match="nested more than"):
        nest(course, ContentTrack.MAX_NESTING_DEPTH + 5)


def test_ancestors_terminates_on_a_cycle_already_in_the_data(db, course):
    """Validation cannot reach rows written around it, so the walk must not hang on them."""
    innermost = nest(course, 3)
    root = ContentTrack.objects.get(name="t0")
    # .update() skips save(), and with it full_clean() - the only way to get a cycle into
    # the table, and what a hand-written data migration or a raw SQL fix would do.
    ContentTrack.objects.filter(pk=root.pk).update(parent_track=innermost)

    # Re-fetched, as production code always does: the in-memory chain still carries the
    # related objects Django cached when they were created.
    ancestry = ContentTrack.objects.get(pk=innermost.pk).ancestors()

    assert len({track.pk for track in ancestry}) == len(ancestry)
    assert innermost.pk in {track.pk for track in ancestry}


def test_a_cycle_in_existing_data_is_rejected_on_the_next_save(db, course):
    innermost = nest(course, 3)
    root = ContentTrack.objects.get(name="t0")
    ContentTrack.objects.filter(pk=root.pk).update(parent_track=innermost)

    with pytest.raises(ValidationError, match="cycle"):
        ContentTrack.objects.get(pk=innermost.pk).save()
