"""Tutor courses, availability windows, and booked tutoring sessions.

Availability is stored as concrete UTC intervals rather than recurring weekly
rules. That keeps the first implementation free of recurrence and
daylight-saving edge cases; a tutor adds the specific windows they are free.

All intervals are half-open, ``[start_at, end_at)``, so a session ending at
3pm and another starting at 3pm do not collide.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .catalog import is_valid_course

# A booked session is this long. The project has no existing session-duration
# policy, so the student UI offers a single fixed duration.
SESSION_MINUTES = 60

# Course codes are stored as text validated against the catalog rather than as
# a foreign key: the catalog is a bundled data file, not a table. See
# assets/fsc_courses.PROVENANCE.md.
COURSE_CODE_MAX_LENGTH = 32


def validate_course_code(value):
    """Reject a course code the bundled catalog does not list."""
    if not is_valid_course(value):
        raise ValidationError("%(value)s is not a course in the catalog.",
                              params={"value": value})


class TutorCourse(models.Model):
    """A course a tutor offers to teach."""

    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_courses",
    )
    course_code = models.CharField(
        max_length=COURSE_CODE_MAX_LENGTH,
        validators=[validate_course_code],
    )

    class Meta:
        ordering = ["course_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "course_code"],
                name="tutorcourse_unique_per_tutor",
            ),
        ]
        indexes = [
            # The search filters on course first, then joins to the tutor.
            models.Index(fields=["course_code", "tutor"],
                         name="tutorcourse_search_idx"),
        ]

    def __str__(self):
        return f"{self.tutor} teaches {self.course_code}"


class TutorAvailability(models.Model):
    """A concrete window a tutor is free, stored in UTC."""

    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    class Meta:
        ordering = ["start_at"]
        verbose_name_plural = "tutor availability"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_at__lt=models.F("end_at")),
                name="tutoravailability_start_before_end",
            ),
            models.UniqueConstraint(
                fields=["tutor", "start_at", "end_at"],
                name="tutoravailability_no_duplicate_window",
            ),
        ]
        indexes = [
            models.Index(fields=["tutor", "start_at", "end_at"],
                         name="tutoravailability_window_idx"),
        ]

    def __str__(self):
        return f"{self.tutor} free {self.start_at} to {self.end_at}"

    def contains(self, start_at, end_at):
        """True when this window fully covers ``[start_at, end_at)``."""
        return self.start_at <= start_at and self.end_at >= end_at


class TutoringSession(models.Model):
    """A booked one-on-one session between a student and a tutor."""

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    # PROTECT, matching TutoringEvent.host: a booking is a record of something
    # that was arranged and must not vanish with an account row.
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="booked_sessions",
    )
    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tutoring_sessions",
    )
    course_code = models.CharField(
        max_length=COURSE_CODE_MAX_LENGTH,
        validators=[validate_course_code],
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_at__lt=models.F("end_at")),
                name="tutoringsession_start_before_end",
            ),
            # SQLite has no exclusion constraints, so arbitrary overlap cannot
            # be enforced declaratively. This catches the common case -- two
            # confirmed bookings for the same tutor at the same start -- at the
            # database level even if application checks are bypassed. Partial
            # overlap is re-checked inside the booking transaction.
            models.UniqueConstraint(
                fields=["tutor", "start_at"],
                condition=models.Q(status="confirmed"),
                name="tutoringsession_one_confirmed_per_tutor_start",
            ),
        ]
        indexes = [
            models.Index(fields=["tutor", "start_at", "end_at", "status"],
                         name="tutoringsession_overlap_idx"),
            models.Index(fields=["student", "start_at"],
                         name="tutoringsession_student_idx"),
        ]

    def __str__(self):
        return f"{self.course_code} with {self.tutor} at {self.start_at}"

    @property
    def is_upcoming(self):
        return self.status == self.Status.CONFIRMED and self.end_at > timezone.now()

    def involves(self, user):
        """True when ``user`` is the student or the tutor on this session."""
        return user.pk in {self.student_id, self.tutor_id}
