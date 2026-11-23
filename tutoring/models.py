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

# A booked session is this long. The project has no existing session-duration
# policy, so the student UI offers a single fixed duration.
SESSION_MINUTES = 60

COURSE_CODE_MAX_LENGTH = 32


def validate_course_code(value):
    """Reject a code that is not an active course.

    No longer attached to a field -- the ``course`` foreign keys enforce
    existence -- but migration 0001 still references it, so it must stay
    importable.
    """
    if not Course.objects.filter(code=value, is_active=True).exists():
        raise ValidationError("%(value)s is not a course in the catalog.",
                              params={"value": value})


class Course(models.Model):
    """One course from the FSC catalog that tutoring can be offered for.

    Seeded from ``assets/fsc_courses.json`` by migration 0002 and maintained
    in the Django admin after that. ``code`` is the stable identifier other
    rows point at (foreign keys use ``to_field="code"``), so the stored value
    in ``TutorCourse`` and ``TutoringSession`` is still the readable code.

    Retire a course with ``is_active`` rather than deleting it: a retired
    course disappears from search, new offers, and new bookings, while past
    sessions keep their course. Deleting is allowed only while no session
    references the course.
    """

    class Level(models.TextChoices):
        UNDERGRADUATE = "undergraduate", "Undergraduate"
        GRADUATE = "graduate", "Graduate"
        # A WRIGHT Foundations requirement met by any course in a group, so it
        # has no single catalog course number.
        FOUNDATION_GROUP = "foundation_group", "Foundations group"

    code = models.CharField(max_length=COURSE_CODE_MAX_LENGTH, unique=True)
    title = models.CharField(max_length=200)
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.UNDERGRADUATE,
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Untick to retire the course: it stops appearing in search "
                  "and cannot be offered or booked, but past sessions keep it.",
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} \u2014 {self.title}"

    def clean(self):
        # Codes are compared exactly everywhere, so stray whitespace would
        # create a near-duplicate that search shows twice.
        self.code = " ".join(self.code.split())
        self.title = " ".join(self.title.split())


class TutorCourse(models.Model):
    """A course a tutor offers to teach."""

    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_courses",
    )
    # Deleting a course withdraws every offer of it; nothing was booked
    # through an offer alone, so there is no history to lose.
    course = models.ForeignKey(
        Course,
        to_field="code",
        on_delete=models.CASCADE,
        related_name="tutor_offers",
    )

    class Meta:
        ordering = ["course"]
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "course"],
                name="tutorcourse_unique_per_tutor",
            ),
        ]
        indexes = [
            # The search filters on course first, then joins to the tutor.
            models.Index(fields=["course", "tutor"],
                         name="tutorcourse_search_idx"),
        ]

    def __str__(self):
        return f"{self.tutor} teaches {self.course_id}"


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
    # PROTECT: a booked session is a record, so its course cannot be deleted
    # out from under it. Retire the course with ``is_active`` instead.
    course = models.ForeignKey(
        Course,
        to_field="code",
        on_delete=models.PROTECT,
        related_name="sessions",
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
        return f"{self.course_id} with {self.tutor} at {self.start_at}"

    @property
    def is_upcoming(self):
        return self.status == self.Status.CONFIRMED and self.end_at > timezone.now()

    def involves(self, user):
        """True when ``user`` is the student or the tutor on this session."""
        return user.pk in {self.student_id, self.tutor_id}
