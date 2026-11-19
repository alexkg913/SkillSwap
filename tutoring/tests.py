"""Tests for the course catalog, tutor matching, and booking."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .catalog import (
    FOUNDATION_GROUP,
    GRADUATE,
    UNDERGRADUATE,
    course_choices,
    course_titles,
    courses,
    is_valid_course,
    search_courses,
)
from .models import SESSION_MINUTES, TutorAvailability, TutorCourse, TutoringSession
from .selectors import search_tutors

User = get_user_model()

COURSE = "MAT 2022"
OTHER_COURSE = "CSC 2290"


def make_user(email, *, is_tutor=False, first_name="", last_name=""):
    return User.objects.create_user(
        username=email.split("@")[0],
        email=email,
        password="test-password",
        is_tutor=is_tutor,
        first_name=first_name,
        last_name=last_name,
    )


def at(hour, *, days=1, minutes=0):
    """A future aware datetime, rounded to the hour, for readable intervals."""
    base = (timezone.now() + timedelta(days=days)).replace(
        hour=hour, minute=minutes, second=0, microsecond=0
    )
    return base


class CourseCatalogTests(TestCase):
    """The course catalog is read from assets/fsc_courses.json."""

    def test_catalog_loads_and_codes_are_unique(self):
        rows = courses()

        self.assertGreater(len(rows), 1000)
        codes = [code for code, _, _ in rows]
        self.assertEqual(len(codes), len(set(codes)))

    def test_every_entry_has_a_code_title_and_known_level(self):
        for code, title, level in courses():
            with self.subTest(code):
                self.assertTrue(code.strip())
                self.assertTrue(title.strip())
                self.assertIn(level, {UNDERGRADUATE, GRADUATE, FOUNDATION_GROUP})

    def test_choices_pair_the_code_with_a_code_and_title_label(self):
        self.assertIn(
            ("MAT 2022", "MAT 2022 \u2014 Elementary Statistics"),
            course_choices(),
        )

    def test_choices_can_be_filtered_by_level(self):
        undergraduate = course_choices(UNDERGRADUATE)

        self.assertLess(len(undergraduate), len(course_choices()))
        self.assertIn("MAT 2022", dict(undergraduate))
        # A graduate course must not appear in the undergraduate-only list.
        self.assertNotIn("ACC 6200", dict(undergraduate))

    def test_cross_listed_courses_appear_under_each_canonical_code(self):
        """The catalog describes BIO 3362 and CHE 3362 separately.

        The combined "BIO/CHE 3362" spelling from the degree-requirement
        tables is deliberately not a code.
        """
        titles = course_titles()

        self.assertIn("BIO 3362", titles)
        self.assertIn("CHE 3362", titles)
        self.assertNotIn("BIO/CHE 3362", titles)

    def test_foundations_courses_survived_the_catalog_import(self):
        """Codes the WRIGHT Foundations list offered are still selectable."""
        titles = course_titles()

        for code in ("ENG 1005", "MAT 2022", "BIO 1942", "HON 1700", "SOC 1100"):
            with self.subTest(code):
                self.assertIn(code, titles)

    def test_foundation_group_placeholders_are_kept(self):
        placeholders = dict(course_choices(FOUNDATION_GROUP))

        self.assertIn("MUS XXXX - Ensemble", placeholders)
        self.assertIn("MUS XXXX - Performance", placeholders)

    def test_is_valid_course_rejects_an_unknown_code(self):
        self.assertTrue(is_valid_course("CSC 2290"))
        self.assertFalse(is_valid_course("ZZZ 9999"))
        self.assertFalse(is_valid_course(""))

    def test_titles_are_not_left_in_the_catalog_all_caps_form(self):
        """Headings are all-caps in the PDF; acronyms are the only caps kept."""
        acronyms = {
            "SCUBA", "ESOL", "STEM", "VITA", "IPCE", "AGPC", "CFA", "CPA",
            "DNP", "FNP", "GIS", "US", "VR", "AI", "HR", "FSC",
            # Not acronyms, but correctly left uncased: a grade range and the
            # catalog's placeholder for the year a travel course runs.
            "K-12", "20XX",
        }
        for code, title, _ in courses():
            shouty = [
                word
                for word in title.split()
                if len(word.strip("():,.;&'")) > 3
                and word.strip("():,.;&'").isupper()
                and word.strip("():,.;&'") not in acronyms
            ]
            with self.subTest(code):
                self.assertEqual(shouty, [])


class MatchingTests(TestCase):
    """The search predicate: right course, whole window free, not booked."""

    def setUp(self):
        self.tutor = make_user("tutor@example.edu", is_tutor=True, first_name="Ada")
        self.start_at = at(14)
        self.end_at = self.start_at + timedelta(minutes=SESSION_MINUTES)

    def offer(self, course=COURSE):
        return TutorCourse.objects.create(tutor=self.tutor, course_code=course)

    def free(self, start_at, end_at):
        return TutorAvailability.objects.create(
            tutor=self.tutor, start_at=start_at, end_at=end_at
        )

    def search(self, course=COURSE):
        return search_tutors(course, self.start_at, self.end_at)

    def test_tutor_matches_when_course_and_window_line_up(self):
        self.offer()
        self.free(self.start_at, self.end_at)

        results = self.search()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["tutor_name"], "Ada")
        self.assertEqual(results[0]["course_code"], COURSE)

    def test_window_wider_than_the_request_still_matches(self):
        self.offer()
        self.free(self.start_at - timedelta(hours=2), self.end_at + timedelta(hours=2))

        self.assertEqual(len(self.search()), 1)

    def test_availability_for_another_course_does_not_match(self):
        self.offer(OTHER_COURSE)
        self.free(self.start_at, self.end_at)

        self.assertEqual(self.search(COURSE), [])

    def test_partially_overlapping_window_does_not_match(self):
        """Half a session is not a session."""
        self.offer()
        self.free(self.start_at, self.end_at - timedelta(minutes=30))

        self.assertEqual(self.search(), [])

    def test_window_starting_after_the_request_does_not_match(self):
        self.offer()
        self.free(self.start_at + timedelta(minutes=15), self.end_at + timedelta(hours=1))

        self.assertEqual(self.search(), [])

    def test_tutor_with_no_availability_does_not_match(self):
        self.offer()

        self.assertEqual(self.search(), [])

    def test_account_that_is_not_a_tutor_never_matches(self):
        self.tutor.is_tutor = False
        self.tutor.save(update_fields=["is_tutor"])
        self.offer()
        self.free(self.start_at, self.end_at)

        self.assertEqual(self.search(), [])

    def test_confirmed_overlapping_session_excludes_the_tutor(self):
        self.offer()
        self.free(self.start_at - timedelta(hours=1), self.end_at + timedelta(hours=1))
        TutoringSession.objects.create(
            student=make_user("other@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=self.start_at + timedelta(minutes=30),
            end_at=self.end_at + timedelta(minutes=30),
            status=TutoringSession.Status.CONFIRMED,
        )

        self.assertEqual(self.search(), [])

    def test_cancelled_session_does_not_exclude_the_tutor(self):
        self.offer()
        self.free(self.start_at, self.end_at)
        TutoringSession.objects.create(
            student=make_user("other@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=self.start_at,
            end_at=self.end_at,
            status=TutoringSession.Status.CANCELLED,
        )

        self.assertEqual(len(self.search()), 1)

    def test_back_to_back_sessions_are_allowed(self):
        """Half-open intervals: a session ending at the start does not clash."""
        self.offer()
        self.free(self.start_at - timedelta(hours=1), self.end_at)
        TutoringSession.objects.create(
            student=make_user("other@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=self.start_at - timedelta(minutes=SESSION_MINUTES),
            end_at=self.start_at,
            status=TutoringSession.Status.CONFIRMED,
        )

        self.assertEqual(len(self.search()), 1)

    def test_session_starting_exactly_at_the_request_end_is_allowed(self):
        self.offer()
        self.free(self.start_at, self.end_at + timedelta(hours=1))
        TutoringSession.objects.create(
            student=make_user("other@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=self.end_at,
            end_at=self.end_at + timedelta(minutes=SESSION_MINUTES),
            status=TutoringSession.Status.CONFIRMED,
        )

        self.assertEqual(len(self.search()), 1)

    def test_results_never_expose_the_account_email_or_uuid(self):
        self.offer()
        self.free(self.start_at, self.end_at)

        payload = self.search()[0]

        serialized = repr(payload)
        self.assertNotIn(self.tutor.email, serialized)
        self.assertNotIn(str(self.tutor.pk), serialized)

    def test_two_tutors_are_returned_in_a_deterministic_order(self):
        self.offer()
        self.free(self.start_at, self.end_at)
        second = make_user("bea@example.edu", is_tutor=True, first_name="Bea")
        TutorCourse.objects.create(tutor=second, course_code=COURSE)
        TutorAvailability.objects.create(
            tutor=second, start_at=self.start_at, end_at=self.end_at
        )

        names = [row["tutor_name"] for row in self.search()]

        self.assertEqual(names, ["Ada", "Bea"])


class RoleAccessTests(TestCase):
    """Role rules are enforced server-side, not by hiding links."""

    def setUp(self):
        self.student = make_user("student@example.edu")
        self.tutor = make_user("tutor@example.edu", is_tutor=True)

    def test_new_account_defaults_to_student(self):
        self.assertFalse(make_user("fresh@example.edu").is_tutor)

    def test_anonymous_visitor_is_sent_to_login(self):
        for name in ("tutoring:find", "tutoring:setup", "tutoring:availability",
                     "tutoring:sessions"):
            with self.subTest(name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])

    def test_student_cannot_open_tutor_only_pages(self):
        self.client.force_login(self.student)

        for name in ("tutoring:setup", "tutoring:availability"):
            with self.subTest(name):
                response = self.client.get(reverse(name))
                self.assertRedirects(response, reverse("tutoring:find"))

    def test_student_cannot_post_tutor_courses(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": [COURSE]})

        self.assertRedirects(response, reverse("tutoring:find"))
        self.assertFalse(TutorCourse.objects.exists())

    def test_student_cannot_post_availability(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse("tutoring:availability"), {
            "start_at": timezone.localtime(at(9)).strftime("%Y-%m-%dT%H:%M"),
            "end_at": timezone.localtime(at(11)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertRedirects(response, reverse("tutoring:find"))
        self.assertFalse(TutorAvailability.objects.exists())

    def test_tutor_cannot_open_the_search_page(self):
        self.client.force_login(self.tutor)

        response = self.client.get(reverse("tutoring:find"))

        self.assertRedirects(response, reverse("tutoring:availability"))

    def test_tutor_cannot_delete_another_tutors_window(self):
        other = make_user("other-tutor@example.edu", is_tutor=True)
        window = TutorAvailability.objects.create(
            tutor=other, start_at=at(9), end_at=at(11)
        )
        self.client.force_login(self.tutor)

        response = self.client.post(
            reverse("tutoring:delete_availability", args=[window.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(TutorAvailability.objects.filter(pk=window.pk).exists())

    def test_availability_delete_rejects_get(self):
        window = TutorAvailability.objects.create(
            tutor=self.tutor, start_at=at(9), end_at=at(11)
        )
        self.client.force_login(self.tutor)

        response = self.client.get(
            reverse("tutoring:delete_availability", args=[window.pk])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(TutorAvailability.objects.filter(pk=window.pk).exists())


class TutorSetupTests(TestCase):
    def setUp(self):
        self.tutor = make_user("tutor@example.edu", is_tutor=True)
        self.client.force_login(self.tutor)

    def test_tutor_saves_and_replaces_their_courses(self):
        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": [COURSE, OTHER_COURSE]})

        self.assertRedirects(response, reverse("tutoring:setup"))
        self.assertEqual(
            set(TutorCourse.objects.values_list("course_code", flat=True)),
            {COURSE, OTHER_COURSE},
        )

        # Saving a smaller set removes the ones that were deselected.
        self.client.post(reverse("tutoring:setup"), {"course_codes": [COURSE]})
        self.assertEqual(
            list(TutorCourse.objects.values_list("course_code", flat=True)), [COURSE]
        )

    def test_a_course_outside_the_catalog_is_rejected(self):
        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": ["ZZZ 9999"]})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TutorCourse.objects.exists())

    def test_the_page_does_not_ship_the_whole_catalog(self):
        """The picker searches; it does not render ~960 options."""
        response = self.client.get(reverse("tutoring:setup"))

        self.assertContains(response, 'class="course-picker')
        self.assertContains(response, 'data-search-url="%s"'
                            % reverse("tutoring:course_options"))
        # A rendered catalog would show up as a wall of <option> elements.
        self.assertLess(response.content.count(b"<option"), 10)
        self.assertNotContains(response, "Advanced Auditing")

    def test_window_must_end_after_it_starts(self):
        local = timezone.localtime(at(10))
        response = self.client.post(reverse("tutoring:availability"), {
            "start_at": local.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (local - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TutorAvailability.objects.exists())

    def test_window_in_the_past_is_rejected(self):
        past = timezone.localtime(timezone.now() - timedelta(days=1))
        response = self.client.post(reverse("tutoring:availability"), {
            "start_at": past.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (past + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TutorAvailability.objects.exists())

    def test_overlapping_window_is_rejected(self):
        TutorAvailability.objects.create(tutor=self.tutor, start_at=at(9), end_at=at(12))
        local = timezone.localtime(at(11))

        response = self.client.post(reverse("tutoring:availability"), {
            "start_at": local.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (local + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TutorAvailability.objects.count(), 1)

    def test_window_shorter_than_a_session_is_rejected(self):
        local = timezone.localtime(at(9))

        response = self.client.post(reverse("tutoring:availability"), {
            "start_at": local.strftime("%Y-%m-%dT%H:%M"),
            "end_at": (local + timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TutorAvailability.objects.exists())

    def test_window_covering_a_booked_session_cannot_be_deleted(self):
        window = TutorAvailability.objects.create(
            tutor=self.tutor, start_at=at(9), end_at=at(12)
        )
        TutoringSession.objects.create(
            student=make_user("student@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=at(10),
            end_at=at(11),
        )

        response = self.client.post(
            reverse("tutoring:delete_availability", args=[window.pk])
        )

        self.assertRedirects(response, reverse("tutoring:availability"))
        self.assertTrue(TutorAvailability.objects.filter(pk=window.pk).exists())

    def test_free_window_can_be_deleted(self):
        window = TutorAvailability.objects.create(
            tutor=self.tutor, start_at=at(9), end_at=at(12)
        )

        response = self.client.post(
            reverse("tutoring:delete_availability", args=[window.pk])
        )

        self.assertRedirects(response, reverse("tutoring:availability"))
        self.assertFalse(TutorAvailability.objects.filter(pk=window.pk).exists())


class SearchViewTests(TestCase):
    def setUp(self):
        self.student = make_user("student@example.edu")
        self.tutor = make_user("tutor@example.edu", is_tutor=True, first_name="Ada")
        self.start_at = at(14)
        TutorCourse.objects.create(tutor=self.tutor, course_code=COURSE)
        TutorAvailability.objects.create(
            tutor=self.tutor,
            start_at=self.start_at,
            end_at=self.start_at + timedelta(hours=3),
        )
        self.client.force_login(self.student)

    def search_params(self, **overrides):
        params = {
            "course_code": COURSE,
            "start_at": timezone.localtime(self.start_at).strftime("%Y-%m-%dT%H:%M"),
        }
        params.update(overrides)
        return params

    def test_unsearched_page_does_not_claim_there_are_no_tutors(self):
        response = self.client.get(reverse("tutoring:find"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
        self.assertNotContains(response, "No tutors are available")

    def test_search_lists_a_matching_tutor_with_a_book_action(self):
        response = self.client.get(reverse("tutoring:find"), self.search_params())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada")
        self.assertContains(response, "Book Session")

    def test_search_with_no_match_shows_the_empty_message(self):
        response = self.client.get(
            reverse("tutoring:find"), self.search_params(course_code=OTHER_COURSE)
        )

        self.assertContains(response, "No tutors are available for this course")

    def test_past_start_time_is_rejected(self):
        past = timezone.localtime(timezone.now() - timedelta(days=1))
        response = self.client.get(
            reverse("tutoring:find"),
            self.search_params(start_at=past.strftime("%Y-%m-%dT%H:%M")),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
        self.assertFormError(response.context["form"], "start_at",
                             "Pick a start time in the future.")

    def test_invalid_date_is_rejected(self):
        response = self.client.get(
            reverse("tutoring:find"), self.search_params(start_at="not-a-date")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])

    def test_course_outside_the_catalog_is_rejected(self):
        response = self.client.get(
            reverse("tutoring:find"), self.search_params(course_code="ZZZ 9999")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])

    def test_search_page_does_not_leak_the_tutors_email(self):
        response = self.client.get(reverse("tutoring:find"), self.search_params())

        self.assertNotContains(response, self.tutor.email)
        self.assertNotContains(response, str(self.tutor.pk))


class BookingTests(TestCase):
    def setUp(self):
        self.student = make_user("student@example.edu")
        self.tutor = make_user("tutor@example.edu", is_tutor=True, first_name="Ada")
        self.start_at = at(14)
        self.end_at = self.start_at + timedelta(minutes=SESSION_MINUTES)
        self.tutor_course = TutorCourse.objects.create(
            tutor=self.tutor, course_code=COURSE
        )
        self.window = TutorAvailability.objects.create(
            tutor=self.tutor, start_at=self.start_at, end_at=self.start_at + timedelta(hours=3)
        )
        self.client.force_login(self.student)

    def post_data(self, **overrides):
        data = {
            "tutor_course": self.tutor_course.pk,
            "start_at": self.start_at.isoformat(),
        }
        data.update(overrides)
        return data

    def book(self, **overrides):
        return self.client.post(reverse("tutoring:book"), self.post_data(**overrides))

    def test_booking_creates_a_confirmed_session_for_the_signed_in_student(self):
        response = self.book()

        self.assertRedirects(response, reverse("tutoring:sessions"))
        session = TutoringSession.objects.get()
        self.assertEqual(session.student, self.student)
        self.assertEqual(session.tutor, self.tutor)
        self.assertEqual(session.course_code, COURSE)
        self.assertEqual(session.start_at, self.start_at)
        self.assertEqual(session.end_at, self.end_at)
        self.assertEqual(session.status, TutoringSession.Status.CONFIRMED)

    def test_student_identity_comes_from_the_session_not_the_post_body(self):
        impostor = make_user("impostor@example.edu")

        self.book(student=impostor.pk)

        self.assertEqual(TutoringSession.objects.get().student, self.student)

    def test_booking_rejects_get(self):
        response = self.client.get(reverse("tutoring:book"))

        self.assertEqual(response.status_code, 405)
        self.assertFalse(TutoringSession.objects.exists())

    def test_anonymous_booking_is_sent_to_login(self):
        self.client.logout()

        response = self.book()

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertFalse(TutoringSession.objects.exists())

    def test_tutor_account_cannot_book(self):
        self.client.force_login(self.tutor)

        response = self.book()

        self.assertRedirects(response, reverse("tutoring:availability"))
        self.assertFalse(TutoringSession.objects.exists())

    def test_booking_a_time_outside_availability_is_refused(self):
        response = self.book(start_at=(self.start_at + timedelta(days=2)).isoformat())

        self.assertEqual(response.status_code, 303)
        self.assertFalse(TutoringSession.objects.exists())

    def test_booking_an_already_taken_slot_is_refused(self):
        TutoringSession.objects.create(
            student=make_user("first@example.edu"),
            tutor=self.tutor,
            course_code=COURSE,
            start_at=self.start_at,
            end_at=self.end_at,
        )

        response = self.book()

        self.assertEqual(response.status_code, 303)
        self.assertIn(reverse("tutoring:find"), response["Location"])
        self.assertEqual(TutoringSession.objects.count(), 1)

    def test_booking_is_refused_once_the_tutor_stops_being_a_tutor(self):
        """Caught at form validation, before the booking transaction.

        The transaction re-checks the flag too, for the case where it changes
        between validation and the insert.
        """
        self.tutor.is_tutor = False
        self.tutor.save(update_fields=["is_tutor"])

        response = self.book()

        self.assertIn(response.status_code, (302, 303))
        self.assertIn(reverse("tutoring:find"), response["Location"])
        self.assertFalse(TutoringSession.objects.exists())

    def test_booking_after_the_window_was_removed_is_refused(self):
        """A search result is informational, never a reservation."""
        self.window.delete()

        response = self.book()

        self.assertEqual(response.status_code, 303)
        self.assertFalse(TutoringSession.objects.exists())

    def test_a_second_identical_booking_cannot_be_created(self):
        self.book()
        other_student = make_user("second@example.edu")
        self.client.force_login(other_student)

        response = self.book()

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            TutoringSession.objects.filter(
                status=TutoringSession.Status.CONFIRMED
            ).count(),
            1,
        )

    def test_database_refuses_two_confirmed_sessions_at_one_tutors_start(self):
        """The partial unique constraint is the last line of defence.

        Application checks are what normally prevent this; the constraint
        holds even if they are bypassed.
        """
        from django.db import IntegrityError, transaction

        TutoringSession.objects.create(
            student=self.student, tutor=self.tutor, course_code=COURSE,
            start_at=self.start_at, end_at=self.end_at,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TutoringSession.objects.create(
                    student=make_user("clash@example.edu"), tutor=self.tutor,
                    course_code=COURSE, start_at=self.start_at, end_at=self.end_at,
                )

    def test_cancelled_session_frees_the_slot_again(self):
        self.book()
        session = TutoringSession.objects.get()
        session.status = TutoringSession.Status.CANCELLED
        session.save(update_fields=["status"])

        self.assertEqual(len(search_tutors(COURSE, self.start_at, self.end_at)), 1)


class SessionListAndCancelTests(TestCase):
    def setUp(self):
        self.student = make_user("student@example.edu", first_name="Sam")
        self.tutor = make_user("tutor@example.edu", is_tutor=True, first_name="Ada")
        self.session = TutoringSession.objects.create(
            student=self.student, tutor=self.tutor, course_code=COURSE,
            start_at=at(14), end_at=at(15),
        )

    def test_student_sees_their_session_and_the_tutors_name(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("tutoring:sessions"))

        self.assertContains(response, COURSE)
        self.assertContains(response, "Ada")

    def test_tutor_sees_the_same_session_from_the_other_side(self):
        self.client.force_login(self.tutor)

        response = self.client.get(reverse("tutoring:sessions"))

        self.assertContains(response, COURSE)
        self.assertContains(response, "Sam")

    def test_an_unrelated_account_sees_nothing(self):
        self.client.force_login(make_user("nosy@example.edu"))

        response = self.client.get(reverse("tutoring:sessions"))

        self.assertNotContains(response, COURSE)

    def test_either_participant_can_cancel(self):
        for user in (self.student, self.tutor):
            with self.subTest(user.email):
                self.session.status = TutoringSession.Status.CONFIRMED
                self.session.save(update_fields=["status"])
                self.client.force_login(user)

                response = self.client.post(
                    reverse("tutoring:cancel", args=[self.session.pk])
                )

                self.assertRedirects(response, reverse("tutoring:sessions"))
                self.session.refresh_from_db()
                self.assertEqual(self.session.status, TutoringSession.Status.CANCELLED)

    def test_a_non_participant_cannot_cancel(self):
        self.client.force_login(make_user("nosy@example.edu"))

        response = self.client.post(
            reverse("tutoring:cancel", args=[self.session.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, TutoringSession.Status.CONFIRMED)

    def test_cancelling_is_never_a_row_delete(self):
        self.client.force_login(self.student)

        self.client.post(reverse("tutoring:cancel", args=[self.session.pk]))

        self.assertTrue(TutoringSession.objects.filter(pk=self.session.pk).exists())

    def test_cancel_rejects_get(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("tutoring:cancel", args=[self.session.pk]))

        self.assertEqual(response.status_code, 405)


class TimezoneTests(TestCase):
    """Local entry, UTC storage, and the two daylight-saving transitions.

    TIME_ZONE is America/New_York, so spring forward skips 02:00-03:00 local
    and autumn back repeats 01:00-02:00 local. A session time that a student
    cannot actually mean must be refused rather than silently resolved.
    """

    def setUp(self):
        self.tutor = make_user("tutor@example.edu", is_tutor=True)
        self.student = make_user("student@example.edu")
        TutorCourse.objects.create(tutor=self.tutor, course_code=COURSE)
        self.client.force_login(self.student)

    def test_a_local_time_is_stored_as_utc(self):
        from zoneinfo import ZoneInfo

        eastern = ZoneInfo("America/New_York")
        local_start = (timezone.now().astimezone(eastern) + timedelta(days=10)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        TutorAvailability.objects.create(
            tutor=self.tutor, start_at=local_start, end_at=local_start + timedelta(hours=2)
        )

        response = self.client.get(reverse("tutoring:find"), {
            "course_code": COURSE,
            "start_at": local_start.strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertEqual(len(response.context["results"]), 1)
        # The interval the view resolved is the same instant the student meant.
        self.assertEqual(response.context["interval"][0], local_start)
        self.assertEqual(response.context["interval"][0].utcoffset(),
                         local_start.utcoffset())

    def test_a_local_time_that_does_not_exist_is_rejected(self):
        """02:30 on a spring-forward date never happens in Eastern time."""
        response = self.client.get(reverse("tutoring:find"), {
            "course_code": COURSE,
            "start_at": "2027-03-14T02:30",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
        self.assertTrue(response.context["form"].errors)

    def test_an_ambiguous_local_time_is_rejected(self):
        """01:30 on an autumn-back date happens twice in Eastern time."""
        response = self.client.get(reverse("tutoring:find"), {
            "course_code": COURSE,
            "start_at": "2027-11-07T01:30",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
        self.assertTrue(response.context["form"].errors)

    def test_a_session_booked_across_spring_forward_keeps_its_instant(self):
        """A booking submits an offset-qualified time, so it cannot drift.

        Asserted in UTC, which is the storage contract. Wall-clock arithmetic
        across the gap is ambiguous by construction -- 02:30 local does not
        exist on this date -- so comparing local times here would test
        CPython's gap semantics rather than the booking.
        """
        from datetime import timezone as dtz
        from zoneinfo import ZoneInfo

        eastern = ZoneInfo("America/New_York")
        # 01:30 EST, half an hour before the gap, and unambiguous.
        start_at = timezone.datetime(2027, 3, 14, 1, 30, tzinfo=eastern)
        if start_at < timezone.now():
            start_at = timezone.datetime(2028, 3, 12, 1, 30, tzinfo=eastern)
        start_utc = start_at.astimezone(dtz.utc)

        tutor_course = TutorCourse.objects.get(tutor=self.tutor)
        TutorAvailability.objects.create(
            tutor=self.tutor, start_at=start_at, end_at=start_at + timedelta(hours=5)
        )

        response = self.client.post(reverse("tutoring:book"), {
            "tutor_course": tutor_course.pk,
            "start_at": start_at.isoformat(),
        })

        self.assertRedirects(response, reverse("tutoring:sessions"))
        session = TutoringSession.objects.get()
        self.assertEqual(session.start_at.astimezone(dtz.utc), start_utc)
        # Exactly SESSION_MINUTES of real elapsed time, not a wall-clock hour
        # that the transition would stretch or collapse.
        self.assertEqual(
            session.end_at.astimezone(dtz.utc) - session.start_at.astimezone(dtz.utc),
            timedelta(minutes=SESSION_MINUTES),
        )

    def test_pages_state_the_timezone_they_display(self):
        response = self.client.get(reverse("tutoring:find"))

        self.assertContains(response, "Eastern Time")


class CourseSearchTests(TestCase):
    """The ranked substring search behind the course picker."""

    LEVELS = (UNDERGRADUATE, FOUNDATION_GROUP)

    def search(self, query, **kwargs):
        return [code for code, _ in search_courses(query, self.LEVELS, **kwargs)]

    def test_empty_query_returns_nothing(self):
        self.assertEqual(self.search(""), [])
        self.assertEqual(self.search("   "), [])

    def test_exact_code_is_found(self):
        self.assertEqual(self.search("MAT 2022"), ["MAT 2022"])

    def test_code_matching_ignores_case_and_spacing(self):
        for query in ("mat 2022", "MAT2022", "mat2022", "  MAT   2022 "):
            with self.subTest(query):
                self.assertIn("MAT 2022", self.search(query))

    def test_code_prefix_lists_that_subject(self):
        results = self.search("csc")

        self.assertTrue(results)
        self.assertTrue(all(code.startswith("CSC") for code in results))

    def test_title_words_are_searchable(self):
        self.assertIn("MAT 2022", self.search("statistics"))
        self.assertIn("BIO 1942", self.search("scuba"))

    def test_multi_word_query_matches_on_separate_tokens(self):
        """"intro to soc" is not a substring of "Introduction to Sociology"."""
        self.assertIn("SOC 1100", self.search("intro to soc"))

    def test_code_prefix_outranks_a_title_match(self):
        results = self.search("mat")

        self.assertTrue(results[0].startswith("MAT"))

    def test_results_are_bounded(self):
        self.assertLessEqual(len(self.search("a", limit=5)), 5)
        self.assertLessEqual(len(self.search("e")), 20)

    def test_unknown_query_returns_nothing(self):
        self.assertEqual(self.search("zzzzz"), [])

    def test_graduate_courses_are_excluded_from_the_tutoring_levels(self):
        self.assertEqual(self.search("ACC 6200"), [])
        # ...but exist in the catalog when no level filter is applied.
        self.assertIn("ACC 6200", [code for code, _ in search_courses("ACC 6200")])

    def test_foundation_group_entries_are_searchable(self):
        self.assertIn("MUS XXXX - Ensemble", self.search("ensemble"))

    def test_a_very_long_query_is_truncated_not_rejected(self):
        self.assertEqual(self.search("mat 2022" + "x" * 500), [])


class CourseOptionsEndpointTests(TestCase):
    def setUp(self):
        self.url = reverse("tutoring:course_options")
        self.user = make_user("student@example.edu")

    def test_requires_login(self):
        response = self.client.get(self.url, {"q": "mat"})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_returns_matching_courses_with_a_display_label(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "MAT 2022"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        courses_payload = response.json()["courses"]
        self.assertEqual(len(courses_payload), 1)
        self.assertEqual(courses_payload[0], {
            "code": "MAT 2022",
            "title": "Elementary Statistics",
            "label": "MAT 2022 — Elementary Statistics",
        })

    def test_blank_query_returns_an_empty_list(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["courses"], [])

    def test_graduate_courses_are_never_returned(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "advanced auditing"})

        self.assertEqual(response.json()["courses"], [])

    def test_response_is_not_cached(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"q": "mat"})

        self.assertIn("no-store", response["Cache-Control"])

    def test_a_tutor_may_also_search(self):
        """Both pickers use this endpoint."""
        self.client.force_login(make_user("tutor@example.edu", is_tutor=True))

        response = self.client.get(self.url, {"q": "mat 2022"})

        self.assertEqual(len(response.json()["courses"]), 1)


class CoursePickerMarkupTests(TestCase):
    """The picker replaces a ~960-option <select> on both pages."""

    def test_find_page_renders_a_combobox_not_a_catalog(self):
        self.client.force_login(make_user("student@example.edu"))

        response = self.client.get(reverse("tutoring:find"))

        self.assertContains(response, 'role="combobox"')
        self.assertContains(response, 'data-mode="single"')
        self.assertContains(response, 'data-search-url="%s"'
                            % reverse("tutoring:course_options"))
        self.assertContains(response, "tutoring/js/course_search.js")
        self.assertLess(response.content.count(b"<option"), 10)

    def test_find_page_is_small_enough_to_be_worth_it(self):
        """Regression guard: rendering the catalog cost about 75 KB."""
        self.client.force_login(make_user("student@example.edu"))

        response = self.client.get(reverse("tutoring:find"))

        self.assertLess(len(response.content), 20000)

    def test_setup_page_renders_the_multi_select_picker(self):
        self.client.force_login(make_user("tutor@example.edu", is_tutor=True))

        response = self.client.get(reverse("tutoring:setup"))

        self.assertContains(response, 'data-mode="multi"')
        self.assertContains(response, 'class="course-picker__chips"')

    def test_already_chosen_courses_render_as_chips(self):
        tutor = make_user("tutor@example.edu", is_tutor=True)
        TutorCourse.objects.create(tutor=tutor, course_code=COURSE)
        self.client.force_login(tutor)

        response = self.client.get(reverse("tutoring:setup"))

        self.assertContains(response, 'data-code="%s"' % COURSE)
        self.assertContains(response, "Elementary Statistics")
        # The hidden input is what actually submits the value.
        self.assertContains(
            response, '<input type="hidden" name="course_codes" value="%s"' % COURSE
        )

    def test_a_chosen_course_is_shown_in_the_box_when_the_page_re_renders(self):
        """A validation error must not silently drop the chosen course."""
        self.client.force_login(make_user("student@example.edu"))

        response = self.client.get(reverse("tutoring:find"), {
            "course_code": COURSE,
            "start_at": "not-a-date",
        })

        self.assertContains(response, "MAT 2022 — Elementary Statistics")
        self.assertContains(response, 'value="%s"' % COURSE)

    def test_a_course_outside_the_catalog_is_rejected_by_the_hidden_field(self):
        """The box only offers real courses; the server does not trust that."""
        self.client.force_login(make_user("student@example.edu"))

        response = self.client.get(reverse("tutoring:find"), {
            "course_code": "ZZZ 9999",
            "start_at": timezone.localtime(at(14)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertFalse(response.context["searched"])
        self.assertFormError(response.context["form"], "course_code",
                             "Choose a course from the search results.")

    def test_a_graduate_course_cannot_be_submitted_even_though_it_exists(self):
        self.client.force_login(make_user("student@example.edu"))

        response = self.client.get(reverse("tutoring:find"), {
            "course_code": "ACC 6200",
            "start_at": timezone.localtime(at(14)).strftime("%Y-%m-%dT%H:%M"),
        })

        self.assertFalse(response.context["searched"])
        self.assertTrue(response.context["form"].errors)

    def test_a_tutor_cannot_save_a_graduate_course(self):
        self.client.force_login(make_user("tutor@example.edu", is_tutor=True))

        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": ["ACC 6200"]})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(TutorCourse.objects.exists())

    def test_a_blank_fallback_value_clears_courses_instead_of_erroring(self):
        """The no-JS fallback input submits "" when left alone."""
        tutor = make_user("tutor@example.edu", is_tutor=True)
        TutorCourse.objects.create(tutor=tutor, course_code=COURSE)
        self.client.force_login(tutor)

        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": [""]})

        self.assertRedirects(response, reverse("tutoring:setup"))
        self.assertFalse(TutorCourse.objects.exists())

    def test_a_blank_value_alongside_a_real_one_is_ignored(self):
        tutor = make_user("tutor2@example.edu", is_tutor=True)
        self.client.force_login(tutor)

        response = self.client.post(reverse("tutoring:setup"),
                                    {"course_codes": ["", COURSE]})

        self.assertRedirects(response, reverse("tutoring:setup"))
        self.assertEqual(
            list(TutorCourse.objects.values_list("course_code", flat=True)), [COURSE]
        )
