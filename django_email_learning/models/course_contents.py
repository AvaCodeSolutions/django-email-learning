import random
from enum import StrEnum
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import ngettext

from .courses import Course
from .enums.course_content_type import CourseContentType


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


class CourseContent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    priority = models.IntegerField()
    type = models.CharField(
        max_length=50,
        choices=[(t.value, t.name.capitalize()) for t in CourseContentType],
    )
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, null=True, blank=True, on_delete=models.CASCADE)
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
        return f"{self.course.title} content #{self.priority}"

    @property
    def deadline_days(self) -> Optional[int]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.deadline_days
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.deadline_days
        return None

    @property
    def reminder_interval_days(self) -> Optional[int]:
        if self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.reminder_interval_days
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.reminder_interval_days
        return None

    @property
    def title(self) -> str:
        if self.type == CourseContentType.LESSON and self.lesson:
            return self.lesson.title
        elif self.type == CourseContentType.QUIZ and self.quiz:
            return self.quiz.title
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            return self.assignment.title
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
        if self.type == CourseContentType.LESSON and self.lesson:
            self.lesson.full_clean()
        elif self.type == CourseContentType.QUIZ and self.quiz:
            self.quiz.full_clean()
        elif self.type == CourseContentType.ASSIGNMENT and self.assignment:
            self.assignment.full_clean()

    def full_clean(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._validate_content()
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    def get_next(self) -> Optional["CourseContent"]:
        next_content = (
            CourseContent.objects.filter(course=self.course, is_published=True, priority__gt=self.priority)
            .order_by("priority")
            .first()
        )
        return next_content

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
                fields=["course", "priority"],
                name="unique_priority_per_course",
            ),
        ]
