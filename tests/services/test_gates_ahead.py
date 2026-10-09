"""Which content of a course sits behind a gate, for showing it locked on the public page."""

from django_email_learning.models import ContentTrack, ContentTransition, CourseContent, Gate, Lesson
from django_email_learning.services.content_sequence_service import gates_ahead


def add_lesson(course, priority, title, track=None, published=True):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title, content="..."),
        waiting_period=3600,
        is_published=published,
    )


def add_gate(course, priority, key, track=None, published=True):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="gate",
        gate=Gate.objects.create(title=key.title(), key=key),
        waiting_period=3600,
        is_published=published,
    )


def held(course):
    """Titles of held content, mapped to the title of the gate holding each."""
    return {
        CourseContent.objects.get(id=content_id).title: gate.title for content_id, gate in gates_ahead(course).items()
    }


def test_content_after_a_gate_on_the_spine_is_held_by_it(gate_course):
    assert held(gate_course.course) == {"Paid lesson": "Payment"}


def test_an_unpublished_gate_holds_nothing(gate_course):
    gate_course.gate_content.is_published = False
    gate_course.gate_content.save()

    assert held(gate_course.course) == {}


def test_the_nearest_gate_is_named(gate_course):
    add_gate(gate_course.course, 4, "account")
    add_lesson(gate_course.course, 5, "Team lesson")

    assert held(gate_course.course) == {"Paid lesson": "Payment", "Account": "Payment", "Team lesson": "Account"}


def test_a_track_entered_only_from_behind_a_gate_is_held(gate_course, quiz):
    course = gate_course.course
    branch = CourseContent.objects.create(
        course=course, priority=4, type="quiz", quiz=quiz, waiting_period=3600, is_published=True
    )
    track = ContentTrack.objects.create(course=course, name="Extra")
    add_lesson(course, 1, "Extra lesson", track=track)
    ContentTransition.objects.create(source=branch, order=1, condition="passed", target=track)

    assert held(course)["Extra lesson"] == "Payment"


def test_a_gate_on_a_track_holds_only_that_track(course, quiz):
    branch = CourseContent.objects.create(
        course=course, priority=1, type="quiz", quiz=quiz, waiting_period=3600, is_published=True
    )
    add_lesson(course, 2, "Everyone")
    track = ContentTrack.objects.create(course=course, name="Premium")
    add_gate(course, 1, "upgrade", track=track)
    add_lesson(course, 2, "Premium lesson", track=track)
    ContentTransition.objects.create(source=branch, order=1, condition="passed", target=track)

    assert held(course) == {"Premium lesson": "Upgrade"}
