"""Read-side queries for tutoring.

Query logic lives here rather than in the views so views stay focused on
request handling, matching the pattern in events/selectors.py.
"""

from django.db.models import Exists, OuterRef, Q

from .models import TutorAvailability, TutorCourse, TutoringSession


def overlapping_sessions(tutor_field, start_at, end_at):
    """Confirmed sessions for a tutor that clash with ``[start_at, end_at)``.

    Half-open comparison: ``start < end AND end > start``. A session that ends
    exactly when the requested one starts does not overlap, so back-to-back
    bookings are allowed.
    """
    return TutoringSession.objects.filter(
        tutor=tutor_field,
        status=TutoringSession.Status.CONFIRMED,
        start_at__lt=end_at,
        end_at__gt=start_at,
    )


def available_tutor_courses(course, start_at, end_at):
    """``TutorCourse`` rows whose tutor can take ``[start_at, end_at)``.

    ``course`` is a ``Course`` or its code. A row matches when all of these
    hold:

    1. the account is flagged ``is_tutor``;
    2. the row is for the requested course, and that course is not retired;
    3. one availability window *fully contains* the requested interval -- a
       window that only partly covers it is not a match, because the tutor
       would not be free for the whole session;
    4. no confirmed session for that tutor overlaps the interval.

    Returns the ``TutorCourse`` rather than the user so callers have a stable
    public identifier to put in a form without exposing an account UUID.
    """
    covering_window = TutorAvailability.objects.filter(
        tutor=OuterRef("tutor"),
        start_at__lte=start_at,
        end_at__gte=end_at,
    )
    clashing_session = overlapping_sessions(OuterRef("tutor"), start_at, end_at)

    return (
        TutorCourse.objects.filter(
            course=course,
            course__is_active=True,
            tutor__is_tutor=True,
        )
        .annotate(
            has_window=Exists(covering_window),
            is_booked=Exists(clashing_session),
        )
        .filter(has_window=True, is_booked=False)
        .select_related("tutor", "course")
        # Deterministic order: display name, then pk to break ties.
        .order_by("tutor__first_name", "tutor__last_name", "tutor__username", "pk")
    )


def tutor_display_name(user):
    """A tutor's public name.

    Never the email address -- it is this project's ``USERNAME_FIELD`` -- and
    never the account UUID. Falls back to the username when no real name is
    set, the same ordering the profile header uses.
    """
    full_name = user.get_full_name().strip()
    return full_name or user.username


def serialize_tutor_result(tutor_course, start_at, end_at):
    """Public payload for one search result.

    Public fields only: a display name, the major, and the course. The
    identifier is the ``TutorCourse`` primary key, which is what the booking
    form submits; the server resolves the tutor from it, so no account
    identifier reaches the page. Booking re-checks permission regardless --
    hiding an id is not what protects a record.
    """
    tutor = tutor_course.tutor
    return {
        "tutor_course_id": tutor_course.pk,
        "tutor_name": tutor_display_name(tutor),
        "major": tutor.major,
        "course_code": tutor_course.course.code,
        "course_title": tutor_course.course.title,
        "start_at": start_at,
        "end_at": end_at,
    }


def search_tutors(course, start_at, end_at):
    """Search results for the Find a Tutor page."""
    return [
        serialize_tutor_result(tutor_course, start_at, end_at)
        for tutor_course in available_tutor_courses(course, start_at, end_at)
    ]


def courses_for_tutor(tutor):
    """``(code, title)`` for each active course a tutor offers.

    An offer of a retired course is left out, so it drops off the tutor's list
    the next time they save it.
    """
    return list(
        TutorCourse.objects.filter(tutor=tutor, course__is_active=True)
        .order_by("course__code")
        .values_list("course__code", "course__title")
    )


def upcoming_availability(tutor, now):
    """A tutor's future availability windows, earliest first."""
    return TutorAvailability.objects.filter(tutor=tutor, end_at__gt=now).order_by("start_at")


def upcoming_sessions_for(user, now):
    """Confirmed future sessions where ``user`` is the student or the tutor."""
    return (
        TutoringSession.objects.filter(
            Q(student=user) | Q(tutor=user),
            status=TutoringSession.Status.CONFIRMED,
            end_at__gt=now,
        )
        .select_related("student", "tutor", "course")
        .order_by("start_at")
    )


def sessions_covered_by(availability):
    """Confirmed future sessions that rely on this availability window.

    Deleting a window that a booked session sits inside would leave the
    session without any availability behind it, so the tutor UI refuses.
    """
    return overlapping_sessions(
        availability.tutor_id, availability.start_at, availability.end_at
    )
