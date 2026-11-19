"""Views for Find a Tutor and the tutor's own setup pages.

Role rules are enforced here, server-side. Hiding a link is not a permission
check: a student must not be able to reach a tutor-only URL by typing it, and
a tutor must not be able to book themselves a session.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .catalog import course_titles, search_courses
from .forms import (
    TUTORING_COURSE_LEVELS,
    AvailabilityForm,
    BookingForm,
    FindTutorForm,
    TutorCoursesForm,
)
from .models import TutorAvailability, TutorCourse, TutoringSession
from .selectors import (
    courses_for_tutor,
    overlapping_sessions,
    search_tutors,
    sessions_covered_by,
    tutor_display_name,
    upcoming_availability,
    upcoming_sessions_for,
)


def tutor_required(view):
    """Allow only accounts flagged ``is_tutor``."""

    @wraps(view)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if not request.user.is_tutor:
            messages.error(
                request, "That page is for tutor accounts."
            )
            return redirect("tutoring:find")
        return view(request, *args, **kwargs)

    return wrapper


def student_required(view):
    """Allow only accounts that are not tutors.

    One role at a time for the MVP, so a tutor does not book sessions.
    """

    @wraps(view)
    @login_required(login_url="login")
    def wrapper(request, *args, **kwargs):
        if request.user.is_tutor:
            messages.error(
                request, "Tutor accounts cannot book sessions."
            )
            return redirect("tutoring:availability")
        return view(request, *args, **kwargs)

    return wrapper


@login_required(login_url="login")
@never_cache
def course_options(request):
    """Course matches for the search boxes, as JSON.

    Modelled on ``user_profile.views.skill_options``: the catalog is far too
    large to render into a page, so the search box asks for a bounded slice of
    it. Login is required because this is an authenticated app surface, not
    because course codes are private.
    """
    query = request.GET.get("q", "").strip()[:80]
    matches = search_courses(query, TUTORING_COURSE_LEVELS)
    return JsonResponse({
        "courses": [
            {"code": code, "title": title, "label": f"{code} \u2014 {title}"}
            for code, title in matches
        ],
    })


@student_required
def find_tutor(request):
    """Course + time search. Results are informational, not a reservation."""
    form = FindTutorForm(request.GET or None)
    results = None
    interval = None

    # Only search once the student has actually submitted the form, so an
    # unsearched page does not render a misleading "no tutors" message.
    if request.GET and form.is_valid():
        start_at, end_at = form.interval
        interval = (start_at, end_at)
        results = search_tutors(form.cleaned_data["course_code"], start_at, end_at)

    return render(request, "tutoring/find_tutor.html", {
        "form": form,
        "results": results,
        "interval": interval,
        "searched": results is not None,
        "catalog_is_empty": not course_titles(),
        "course_label": form.course_label,
    })


@student_required
@require_POST
def book_session(request):
    """Book a confirmed session, re-checking availability under a transaction.

    A search result is informational. Everything is re-evaluated here because
    another student may have booked the same slot in between.
    """
    form = BookingForm(request.POST)
    if not form.is_valid():
        messages.error(request, "That booking request was not valid. Try searching again.")
        return redirect("tutoring:find")

    tutor_course = form.cleaned_data["tutor_course"]
    start_at, end_at = form.interval
    tutor = tutor_course.tutor

    if tutor == request.user:
        messages.error(request, "You cannot book a session with yourself.")
        return redirect("tutoring:find")

    try:
        with transaction.atomic():
            # select_for_update is a no-op on SQLite, which serialises writes
            # with a database-level write lock instead. The re-checks below are
            # what make the decision correct; the transaction makes the check
            # and the insert atomic.
            locked_course = (
                TutorCourse.objects.select_for_update()
                .select_related("tutor")
                .get(pk=tutor_course.pk)
            )

            if not locked_course.tutor.is_tutor:
                raise _Conflict("That tutor is no longer taking sessions.")

            covered = TutorAvailability.objects.filter(
                tutor=locked_course.tutor,
                start_at__lte=start_at,
                end_at__gte=end_at,
            ).exists()
            if not covered:
                raise _Conflict("That tutor is no longer free at that time.")

            if overlapping_sessions(locked_course.tutor_id, start_at, end_at).exists():
                raise _Conflict("That slot was just booked by someone else.")

            session = TutoringSession.objects.create(
                student=request.user,
                tutor=locked_course.tutor,
                course_code=locked_course.course_code,
                start_at=start_at,
                end_at=end_at,
                status=TutoringSession.Status.CONFIRMED,
            )
    except _Conflict as conflict:
        return _conflict_response(
            request, str(conflict), tutor_course.course_code, start_at
        )
    except IntegrityError:
        # The partial unique constraint caught a concurrent identical booking.
        return _conflict_response(
            request, "That slot was just booked by someone else.",
            tutor_course.course_code, start_at,
        )

    messages.success(
        request,
        "Session confirmed with %s for %s."
        % (tutor_display_name(session.tutor), session.course_code),
    )
    return redirect("tutoring:sessions")


class _Conflict(Exception):
    """A booking precondition failed when re-checked."""


def _conflict_response(request, message, course_code, start_at):
    """Send the student back to refreshed results with a concise message.

    The API equivalent of a 409: the request was well formed but the slot is
    gone. Re-running the search is what makes the next attempt meaningful.
    """
    messages.error(request, message)
    query = f"course_code={course_code}&start_at={timezone.localtime(start_at):%Y-%m-%dT%H:%M}"
    response = HttpResponseRedirect(f"{reverse('tutoring:find')}?{query}")
    response.status_code = 303
    return response


@login_required(login_url="login")
def my_sessions(request):
    """Upcoming confirmed sessions for whoever is signed in."""
    sessions = upcoming_sessions_for(request.user, timezone.now())
    titles = course_titles()
    rows = [
        {
            "session": session,
            "course_title": titles.get(session.course_code, ""),
            "other_party": tutor_display_name(
                session.tutor if session.student_id == request.user.pk else session.student
            ),
            "role": "tutor" if session.student_id == request.user.pk else "student",
        }
        for session in sessions
    ]
    return render(request, "tutoring/my_sessions.html", {"rows": rows})


@login_required(login_url="login")
@require_POST
def cancel_session(request, pk):
    """Cancel a session. POST only, never a row delete.

    Scoped to the signed-in participant, so someone else's session 404s rather
    than revealing that it exists.
    """
    session = get_object_or_404(TutoringSession, pk=pk)
    if not session.involves(request.user):
        # Same shape as events._hosted_by: a non-participant gets a 404.
        return get_object_or_404(TutoringSession, pk=pk, student=request.user)

    if session.status != TutoringSession.Status.CANCELLED:
        session.status = TutoringSession.Status.CANCELLED
        session.save(update_fields=["status"])
        messages.success(request, "That session is cancelled.")

    return redirect("tutoring:sessions")


@tutor_required
def tutor_courses(request):
    """The courses a tutor offers."""
    if request.method == "POST":
        form = TutorCoursesForm(request.POST)
        if form.is_valid():
            _replace_tutor_courses(request.user, form.cleaned_data["course_codes"])
            messages.success(request, "Your courses are saved.")
            return redirect("tutoring:setup")
    else:
        form = TutorCoursesForm(initial={"course_codes": courses_for_tutor(request.user)})

    titles = course_titles()
    selected = [
        {"code": code, "title": titles.get(code, "")}
        for code in courses_for_tutor(request.user)
    ]
    return render(request, "tutoring/tutor_courses.html", {
        "form": form,
        "selected": selected,
        "catalog_is_empty": not titles,
    })


def _replace_tutor_courses(tutor, course_codes):
    """Make the tutor's offered courses exactly ``course_codes``."""
    wanted = set(course_codes)
    with transaction.atomic():
        TutorCourse.objects.filter(tutor=tutor).exclude(course_code__in=wanted).delete()
        existing = set(courses_for_tutor(tutor))
        TutorCourse.objects.bulk_create(
            [TutorCourse(tutor=tutor, course_code=code) for code in wanted - existing]
        )


@tutor_required
def tutor_availability(request):
    """Add and review availability windows."""
    now = timezone.now()

    if request.method == "POST":
        form = AvailabilityForm(request.POST, tutor=request.user)
        if form.is_valid():
            window = form.save(commit=False)
            # Ownership comes from the session, never from submitted data.
            window.tutor = request.user
            window.save()
            messages.success(request, "Availability added.")
            return redirect("tutoring:availability")
    else:
        form = AvailabilityForm(tutor=request.user)

    return render(request, "tutoring/availability.html", {
        "form": form,
        "windows": upcoming_availability(request.user, now),
        "sessions": upcoming_sessions_for(request.user, now),
        "has_courses": bool(courses_for_tutor(request.user)),
    })


@tutor_required
@require_POST
def delete_availability(request, pk):
    """Remove a window, unless a booked session depends on it."""
    # Scoped by tutor, so another account's window 404s.
    window = get_object_or_404(TutorAvailability, pk=pk, tutor=request.user)

    if sessions_covered_by(window).exists():
        messages.error(
            request,
            "A booked session falls inside that window. Cancel the session first.",
        )
        return redirect("tutoring:availability")

    window.delete()
    messages.success(request, "Availability removed.")
    return redirect("tutoring:availability")
