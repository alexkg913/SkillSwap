"""Forms for finding, offering, and booking tutoring.

Datetimes are entered and displayed in the project timezone (Eastern), the
same convention as TutoringEventForm. Django's ``forms.DateTimeField`` attaches
the active timezone on the way in, so everything downstream is UTC-aware. A
local time that does not exist or is ambiguous because of a daylight-saving
transition is rejected there with a clear message rather than guessed at.
"""

from datetime import timedelta

from django import forms
from django.utils import timezone

from .catalog import FOUNDATION_GROUP, UNDERGRADUATE, course_choices, course_titles
from .models import SESSION_MINUTES, TutorAvailability, TutorCourse

# Graduate listings are excluded from the pickers: peer tutoring here is an
# undergraduate activity, and the full 1,174-entry catalog makes for an
# unusable dropdown. Foundations group entries are kept because students pick
# them on their profile.
TUTORING_COURSE_LEVELS = (UNDERGRADUATE, FOUNDATION_GROUP)


def tutoring_course_choices():
    return course_choices(*TUTORING_COURSE_LEVELS)


def course_label(code):
    """The "CODE — Title" label a search box shows for a chosen course."""
    title = course_titles().get(code)
    return f"{code} \u2014 {title}" if title else code


class CourseCodeMultipleField(forms.MultipleChoiceField):
    """Multiple course codes, ignoring blanks.

    The no-JavaScript fallback input submits an empty string when it is left
    alone, which would otherwise fail choice validation and stop a tutor
    clearing their course list.
    """

    def to_python(self, value):
        return [code for code in super().to_python(value) if code.strip()]


class LocalDateTimeField(forms.DateTimeField):
    """A datetime entered in the viewer's local (Eastern) time."""

    widget = forms.DateTimeInput(
        attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
    )


class FindTutorForm(forms.Form):
    """Course and desired start time for a tutoring search."""

    # The value is written by the course search box rather than chosen from a
    # rendered list: 958 <option> elements is both unusable and about 75 KB of
    # markup. The field still validates against every allowed course, so a
    # submitted code is checked server-side regardless of what the page
    # offered. Same trade as the skills picker in user_profile.
    course_code = forms.ChoiceField(
        choices=(),
        label="Course",
        widget=forms.HiddenInput,
        error_messages={"invalid_choice": "Choose a course from the search results."},
    )
    start_at = LocalDateTimeField(
        label="Starts at (Eastern Time)",
        help_text=f"Sessions are {SESSION_MINUTES} minutes long.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assigned here, not at class definition, so the catalog file is read
        # on first use rather than at import.
        self.fields["course_code"].choices = tutoring_course_choices()

    @property
    def course_label(self):
        """Label to show in the search box when the page re-renders."""
        code = (self.data.get("course_code") or "").strip()
        return course_label(code) if code else ""

    def clean_start_at(self):
        start_at = self.cleaned_data["start_at"]
        if start_at < timezone.now():
            raise forms.ValidationError("Pick a start time in the future.")
        return start_at

    @property
    def interval(self):
        """The requested ``(start_at, end_at)``, or ``None`` before validation."""
        start_at = self.cleaned_data.get("start_at")
        if start_at is None:
            return None
        return start_at, start_at + timedelta(minutes=SESSION_MINUTES)


class BookingForm(forms.Form):
    """Confirms one search result.

    The tutor is resolved from ``tutor_course`` server-side; the page never
    submits an account identifier. ``start_at`` is echoed back so a stale
    results page cannot book a different time than the one displayed, and it
    is re-validated against availability inside the booking transaction.
    """

    tutor_course = forms.ModelChoiceField(
        queryset=TutorCourse.objects.none(),
        widget=forms.HiddenInput,
    )
    start_at = forms.DateTimeField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only courses offered by an account that is still a tutor.
        self.fields["tutor_course"].queryset = TutorCourse.objects.filter(
            tutor__is_tutor=True
        ).select_related("tutor")

    def clean_start_at(self):
        start_at = self.cleaned_data["start_at"]
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at)
        if start_at < timezone.now():
            raise forms.ValidationError("That session time has already passed.")
        return start_at

    @property
    def interval(self):
        start_at = self.cleaned_data.get("start_at")
        if start_at is None:
            return None
        return start_at, start_at + timedelta(minutes=SESSION_MINUTES)


class TutorCoursesForm(forms.Form):
    """The set of courses a tutor offers."""

    # Hidden inputs maintained by the search box, for the same reason as
    # FindTutorForm.course_code. Validation still covers the full catalog.
    course_codes = CourseCodeMultipleField(
        choices=(),
        required=False,
        label="Courses you can tutor",
        widget=forms.MultipleHiddenInput,
        error_messages={"invalid_choice": "%(value)s is not a course in the catalog."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course_codes"].choices = tutoring_course_choices()


class AvailabilityForm(forms.ModelForm):
    """One availability window.

    ``tutor`` is deliberately absent from ``Meta.fields``: ownership is
    assigned from ``request.user`` in the view, never from submitted data.
    """

    start_at = LocalDateTimeField(label="From (Eastern Time)")
    end_at = LocalDateTimeField(label="Until (Eastern Time)")

    class Meta:
        model = TutorAvailability
        fields = ["start_at", "end_at"]

    def __init__(self, *args, tutor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tutor = tutor

    def clean_start_at(self):
        start_at = self.cleaned_data["start_at"]
        if start_at < timezone.now():
            raise forms.ValidationError(
                "That window is in the past. Add times students can still book."
            )
        return start_at

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get("start_at")
        end_at = cleaned_data.get("end_at")

        if start_at is None or end_at is None:
            return cleaned_data

        if end_at <= start_at:
            raise forms.ValidationError("The end time must be after the start time.")

        if end_at - start_at < timedelta(minutes=SESSION_MINUTES):
            raise forms.ValidationError(
                f"A window needs to be at least {SESSION_MINUTES} minutes "
                "long for a session to fit inside it."
            )

        if self.tutor is not None:
            # Overlapping windows would let the same free time be matched
            # twice and make the tutor's own list confusing to read.
            clash = TutorAvailability.objects.filter(
                tutor=self.tutor, start_at__lt=end_at, end_at__gt=start_at
            )
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise forms.ValidationError(
                    "That overlaps a window you have already added."
                )

        return cleaned_data
