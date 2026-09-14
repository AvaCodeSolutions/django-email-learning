import random
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext, ngettext

from .courses import Course
from .enums.course_content_type import CourseContentType
from .validators import validate_safe_name


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self) -> str:
        return self.title


class QuizSelectionStrategy(StrEnum):
    ALL_QUESTIONS = "all"
    RANDOM_QUESTIONS = "random"


class Quiz(models.Model):
    title = models.CharField(max_length=500)
    required_score = models.IntegerField(validators=[MaxValueValidator(100)])
    selection_strategy = models.CharField(
        max_length=50,
        choices=[
            (QuizSelectionStrategy.ALL_QUESTIONS.value, "All Questions"),
            (QuizSelectionStrategy.RANDOM_QUESTIONS.value, "Random Questions"),
        ],
    )
    deadline_days = models.IntegerField(
        help_text="Time limit to complete the quiz in days. 0 indicates no deadline.",
        validators=[MinValueValidator(0)],
    )
    limited_attempts = models.BooleanField(default=True)
    is_blocking = models.BooleanField(default=True)
    reminder_interval_days = models.IntegerField(
        help_text=(
            "For quizzes without a deadline (deadline_days = 0), send a reminder email every N days "
            "until the learner completes the quiz, up to 3 reminders. 0 or empty means no reminders."
        ),
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name_plural = "Quizzes"

    def __str__(self) -> str:
        return self.title

    def validate_questions(self) -> None:
        if not self.questions.exists():
            raise ValidationError("At least one question is required.")

        for question in self.questions.all():
            try:
                question.validate_answers()
            except ValidationError as e:
                raise ValidationError(f"For question '{question.text}', {e.message}")

    def random_question_ids(self) -> list[int]:
        question_ids = list(self.questions.values_list("id", flat=True))
        if self.selection_strategy == QuizSelectionStrategy.ALL_QUESTIONS.value:
            return question_ids
        if len(question_ids) <= 5:
            return question_ids
        number_of_questions = int(max(5, len(question_ids) // 1.5))
        selected_ids = random.sample(question_ids, k=number_of_questions)
        return selected_ids


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    priority = models.IntegerField()

    def __str__(self) -> str:
        return self.text

    def validate_answers(self) -> None:
        if not self.answers.filter(is_correct=True).exists():
            raise ValueError("At least one correct answer is required.")

        if self.answers.count() < 2:
            raise ValueError("At least two answers are required.")

    def is_multiple_choice(self) -> bool:
        return self.answers.filter(is_correct=True).count() > 1


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.text

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:  # type: ignore[no-untyped-def]
        if self.question.quiz.coursecontent_set.filter(is_published=True).exists():
            raise ValidationError("Cannot delete answers from a published quiz.")
        return super().delete(*args, **kwargs)


class Assignment(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_blocking = models.BooleanField(
        default=True,
        help_text="Whether the learner is required to submit the assignment to proceed to the next content.",
    )
    deadline_days = models.IntegerField(
        help_text="Time limit to complete the assignment in days. 0 indicates no deadline.",
        validators=[MinValueValidator(0)],
    )
    requires_text_submission = models.BooleanField(help_text="Whether the assignment requires text submission.")
    requires_file_submission = models.BooleanField(help_text="Whether the assignment requires file submission.")
    reminder_interval_days = models.IntegerField(
        help_text=(
            "For assignments without a deadline (deadline_days = 0), send a reminder email every N days "
            "until the learner submits, up to 3 reminders. 0 or empty means no reminders."
        ),
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return self.title


class DecisionPoint(models.Model):
    """A one-question choice put to a learner, with no right answer.

    The option a learner picks is what the routing rules on its content match, so a course can
    send learners down different tracks by what they say rather than by how they score.
    """

    title = models.CharField(max_length=500)
    prompt = models.TextField()
    deadline_days = models.IntegerField(
        default=0,
        help_text="Time limit to answer in days. 0 indicates no deadline.",
        validators=[MinValueValidator(0)],
    )
    reminder_interval_days = models.IntegerField(
        help_text=(
            "For decisions without a deadline (deadline_days = 0), send a reminder email every N days "
            "until the learner answers, up to 3 reminders. 0 or empty means no reminders."
        ),
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return self.title


class DecisionOption(models.Model):
    decision = models.ForeignKey(DecisionPoint, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    order = models.IntegerField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.text


class ContentTrack(models.Model):
    """A named branch of a course: a run of content a learner takes instead of the main spine.

    Content on a track is ordered by `priority` among its own track only. When a learner
    reaches the end of one, they continue at `merge_into` - the content on an outer track
    where the paths rejoin - or finish the course if it is unset. `parent_track` lets a
    track branch again, and the walk climbs it looking for the first merge point.
    """

    # The longest chain of nested tracks an author may build, counting the track itself.
    # Enforced in clean(); the walk in CourseGraph.ancestors() does not depend on it.
    MAX_NESTING_DEPTH = 10

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="content_tracks")
    name = models.CharField(max_length=200, validators=[validate_safe_name])
    parent_track = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="child_tracks",
        help_text="The track this one branches off. Empty means it branches off the main spine.",
    )
    merge_into = models.ForeignKey(
        "CourseContent",
        null=True,
        blank=True,
        # Clearing the merge point leaves the track ending the course, which is a
        # defined outcome. Cascading would delete a learner's content instead.
        on_delete=models.SET_NULL,
        related_name="merging_tracks",
        help_text="Where a learner continues after the last content on this track. Empty ends the course.",
    )

    class Meta:
        unique_together = [["course", "name"]]

    def __str__(self) -> str:
        return f"{self.course.title}: {self.name}"

    def clean(self) -> None:
        super().clean()
        # The graph reads this module's models, so a module-level import would cycle.
        from django_email_learning.services.course_graph import CourseGraph

        CourseGraph(self.course_id).check_track(self)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:  # type: ignore[no-untyped-def]
        # CourseContent.track is SET_NULL, so deleting a populated track would move its
        # content onto the main spine, where the priorities it carries may already be
        # taken. Refuse instead of raising IntegrityError from the cascade.
        if self.contents.exists():
            raise ValidationError(
                gettext("Cannot delete a track that still has content. Move or delete the content first.")
            )
        if self.child_tracks.exists():
            raise ValidationError(
                gettext("Cannot delete a track that still has nested tracks. Delete or move them first.")
            )
        if self.incoming_transitions.exists():
            raise ValidationError(
                gettext("Cannot delete a track that routing rules still point to. Remove or retarget the rules first.")
            )
        return super().delete(*args, **kwargs)


class CourseContent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    track = models.ForeignKey(
        ContentTrack,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contents",
        help_text="The branch this content belongs to. Empty means the course's main spine.",
    )
    priority = models.IntegerField()
    type = models.CharField(
        max_length=50,
        choices=[(t.value, t.name.capitalize()) for t in CourseContentType],
    )
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, null=True, blank=True, on_delete=models.CASCADE)
    decision = models.ForeignKey(DecisionPoint, null=True, blank=True, on_delete=models.CASCADE)
    waiting_period = models.IntegerField(
        help_text="Waiting period in seconds after previous content is sent or submited."
    )
    is_published = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.type == CourseContentType.LESSON and self.lesson:
            return f"{self.priority} - Lesson: {self.lesson.title}"
        elif self.type == CourseContentType.QUIZ and self.quiz:
            return f"{self.priority} - Quiz: {self.quiz.title}"
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return f"{self.priority} - Assignment: {self.assignment.title}"
        elif self.type == CourseContentType.DECISION and self.decision:
            return f"{self.priority} - Decision: {self.decision.title}"
        return f"{self.course.title} content #{self.priority}"

    @property
    def deadline_days(self) -> Optional[int]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.deadline_days
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.deadline_days
        elif self.type == CourseContentType.DECISION and self.decision:
            return self.decision.deadline_days
        return None

    @property
    def reminder_interval_days(self) -> Optional[int]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.reminder_interval_days
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.reminder_interval_days
        elif self.type == CourseContentType.DECISION and self.decision:
            return self.decision.reminder_interval_days
        return None

    @property
    def is_branch_point(self) -> bool:
        return self.transitions.exists()

    @property
    def title(self) -> str:
        if self.type == CourseContentType.LESSON and self.lesson:
            return self.lesson.title
        elif self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.title
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.title
        elif self.type == CourseContentType.DECISION and self.decision:
            return self.decision.title
        return "Untitled Content"

    @property
    def limited_attempts(self) -> Optional[bool]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.limited_attempts
        return None

    @property
    def is_blocking(self) -> Optional[bool]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.is_blocking
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.is_blocking
        elif self.type == CourseContentType.DECISION and self.decision:
            # A decision has no wrong answer to fail on, so a missed deadline moves the learner on
            # rather than ending the enrollment.
            return False
        return None

    def human_readable_waiting_period(self) -> str:
        if self.waiting_period < 60:
            return ngettext("%(count)d second", "%(count)d seconds", self.waiting_period) % {
                "count": self.waiting_period
            }
        elif self.waiting_period < 3600:
            minutes = self.waiting_period // 60
            return ngettext("%(count)d minute", "%(count)d minutes", minutes) % {"count": minutes}
        elif self.waiting_period < 86400:
            hours = self.waiting_period // 3600
            return ngettext("%(count)d hour", "%(count)d hours", hours) % {"count": hours}
        else:
            days = self.waiting_period // 86400
            return ngettext("%(count)d day", "%(count)d days", days) % {"count": days}

    def _validate_content(self) -> None:
        if self.type == CourseContentType.LESSON and not self.lesson:
            raise ValidationError("Lesson must be provided for lesson content.")
        if self.type == CourseContentType.QUIZ and not self.quiz:
            raise ValidationError("Quiz must be provided for quiz content.")
        if self.type == CourseContentType.ASSIGNMENT and not self.assignment:
            raise ValidationError("Assignment must be provided for assignment content.")
        if self.type == CourseContentType.DECISION and not self.decision:
            raise ValidationError("Decision must be provided for decision content.")
        if self.type == CourseContentType.LESSON and self.lesson:
            self.lesson.full_clean()
        elif self.type == CourseContentType.QUIZ and self.quiz:
            self.quiz.full_clean()
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            self.assignment.full_clean()
        elif self.type == CourseContentType.DECISION and self.decision:
            self.decision.full_clean()

    def full_clean(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._validate_content()
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:  # type: ignore[no-untyped-def]
        # A hard delete cascades to every ContentDelivery for this content and,
        # through them, to learners' quiz/assignment submissions, their feedback,
        # pending DeliverySchedule rows and the delivery history. It also breaks
        # the delivery chain for anyone currently sitting on this content, since
        # the ContentDelivery that would have triggered the next one is gone.
        # Refuse it once the content has reached any learner; the caller can
        # unpublish instead, which DeliverContentsJob handles gracefully by
        # skipping the content and advancing the enrollment.
        if self.contentdelivery_set.exists():
            raise ValidationError(
                gettext(
                    "Cannot delete content that has already been scheduled or delivered to learners. "
                    "Unpublish it instead."
                )
            )
        return super().delete(*args, **kwargs)

    def get_next(self) -> Optional["CourseContent"]:
        # The service reads CourseContent, so a module-level import would cycle.
        from django_email_learning.services import content_sequence_service

        return content_sequence_service.next_content(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "quiz"],
                condition=models.Q(quiz__isnull=False),
                name="unique_quiz_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "lesson"],
                condition=models.Q(lesson__isnull=False),
                name="unique_lesson_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "assignment"],
                condition=models.Q(assignment__isnull=False),
                name="unique_assignment_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "decision"],
                condition=models.Q(decision__isnull=False),
                name="unique_decision_per_course",
            ),
            # Split in two because a single constraint over ("course", "track", "priority")
            # would stop enforcing anything on the main spine: both backends treat NULL
            # track values as distinct from one another, so duplicate priorities there
            # would become legal.
            models.UniqueConstraint(
                fields=["course", "priority"],
                condition=models.Q(track__isnull=True),
                name="unique_priority_per_course_spine",
            ),
            models.UniqueConstraint(
                fields=["course", "track", "priority"],
                condition=models.Q(track__isnull=False),
                name="unique_priority_per_track",
            ),
        ]


@dataclass(frozen=True)
class QuizOutcome:
    """What a learner's quiz submission produced, as the routing rules see it."""

    score: int
    passed: bool


@dataclass(frozen=True)
class DecisionOutcome:
    """The option a learner chose on a decision point, as the routing rules see it."""

    option_id: int


RoutingOutcome = QuizOutcome | DecisionOutcome


class TransitionCondition(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SCORE_GTE = "score_gte"
    SCORE_LT = "score_lt"
    DEFAULT = "default"
    OPTION_SELECTED = "option_selected"


QUIZ_CONDITIONS = frozenset(
    {
        TransitionCondition.PASSED,
        TransitionCondition.FAILED,
        TransitionCondition.SCORE_GTE,
        TransitionCondition.SCORE_LT,
    }
)
THRESHOLD_CONDITIONS = frozenset({TransitionCondition.SCORE_GTE, TransitionCondition.SCORE_LT})
DECISION_CONDITIONS = frozenset({TransitionCondition.OPTION_SELECTED})


class ContentTransition(models.Model):
    """A rule routing a learner from one content onto a `ContentTrack`.

    The rules on a content are evaluated in `order` and the first match wins, so a
    `DEFAULT` rule placed last is the fallback that catches an outcome no earlier rule
    claimed. Content carrying no rules at all is not a branch point and is walked in
    plain priority order.
    """

    source = models.ForeignKey(CourseContent, on_delete=models.CASCADE, related_name="transitions")
    order = models.IntegerField(help_text="Rules are evaluated low to high and the first match wins.")
    condition = models.CharField(
        max_length=50,
        choices=[(c.value, c.name.replace("_", " ").title()) for c in TransitionCondition],
    )
    threshold = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="The score this rule compares against. Required for a score condition.",
    )
    option = models.ForeignKey(
        DecisionOption,
        null=True,
        blank=True,
        # A rule on an option that no longer exists could never match.
        on_delete=models.CASCADE,
        related_name="transitions",
        help_text="The option this rule matches. Required for an option condition.",
    )
    target = models.ForeignKey(ContentTrack, on_delete=models.CASCADE, related_name="incoming_transitions")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "order"], name="unique_transition_order_per_source"),
            models.UniqueConstraint(
                fields=["source"],
                condition=models.Q(condition=TransitionCondition.DEFAULT.value),
                name="single_default_transition_per_source",
            ),
        ]

    def __str__(self) -> str:
        if self.condition in THRESHOLD_CONDITIONS:
            comparison = f" {self.threshold}"
        elif self.condition in DECISION_CONDITIONS and self.option is not None:
            comparison = f" {self.option.text}"
        else:
            comparison = ""
        return f"{self.source.title}: {self.condition}{comparison} -> {self.target.name}"

    @property
    def option_text(self) -> Optional[str]:
        return self.option.text if self.option is not None else None

    def matches(self, outcome: RoutingOutcome) -> bool:
        if self.condition == TransitionCondition.DEFAULT:
            return True
        if isinstance(outcome, DecisionOutcome):
            return self.condition == TransitionCondition.OPTION_SELECTED and self.option_id == outcome.option_id
        if self.condition == TransitionCondition.PASSED:
            return outcome.passed
        if self.condition == TransitionCondition.FAILED:
            return not outcome.passed
        if self.condition == TransitionCondition.SCORE_GTE:
            return self.threshold is not None and outcome.score >= self.threshold
        if self.condition == TransitionCondition.SCORE_LT:
            return self.threshold is not None and outcome.score < self.threshold
        return False

    def clean(self) -> None:
        super().clean()
        if self.condition in THRESHOLD_CONDITIONS and self.threshold is None:
            raise ValidationError({"threshold": "A score condition needs a threshold to compare against."})
        if self.condition not in THRESHOLD_CONDITIONS and self.threshold is not None:
            raise ValidationError({"threshold": "Only a score condition takes a threshold."})
        if self.condition in QUIZ_CONDITIONS and self.source.type != CourseContentType.QUIZ:
            raise ValidationError({"condition": "A quiz condition can only be used on quiz content."})
        if self.condition in DECISION_CONDITIONS:
            if self.source.type != CourseContentType.DECISION:
                raise ValidationError({"condition": "An answer condition can only be used on a decision point."})
            if self.option is None:
                raise ValidationError({"option": "An answer condition needs the answer it matches."})
            if self.option.decision_id != self.source.decision_id:
                raise ValidationError({"option": "The answer must belong to this decision point."})
        elif self.option_id is not None:
            raise ValidationError({"option": "Only an answer condition takes an answer."})
        # The graph reads this module's models, so a module-level import would cycle.
        from django_email_learning.services.course_graph import CourseGraph

        CourseGraph(self.source.course_id).check_transition(self, self.source)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)
