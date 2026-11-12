from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import TutoringEventForm
from .models import CampusLocation, TutoringEvent

User = get_user_model()

# Inside SKILLSWAP_CAMPUS_BBOX; Roux Library's seeded centroid.
ON_CAMPUS = ("28.032497", "-81.948901")


def event_post_data(**overrides):
    data = {
        "title": "Calculus II drop-in",
        "subject": "MAT 2022",
        "tutor": "Sam",
        "date": (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
        "location": "2nd floor study room",
        "latitude": ON_CAMPUS[0],
        "longitude": ON_CAMPUS[1],
        "isPublic": "on",
    }
    data.update(overrides)
    return data


class SeedMigrationTests(TestCase):
    def test_campus_locations_are_seeded(self):
        self.assertTrue(CampusLocation.objects.exists())

    def test_every_seeded_building_sits_inside_the_campus_bbox(self):
        south, west, north, east = settings.SKILLSWAP_CAMPUS_BBOX
        for location in CampusLocation.objects.all():
            with self.subTest(location.name):
                self.assertTrue(south <= float(location.latitude) <= north)
                self.assertTrue(west <= float(location.longitude) <= east)


class AnonymousAccessTests(TestCase):
    """Creating an event requires an account; reading the map does not."""

    def test_anonymous_get_of_create_redirects_to_the_real_login_page(self):
        response = self.client.get(reverse("events:create"))
        self.assertEqual(response.status_code, 302)
        # Regression cover for LOGIN_URL: Django's unset default is
        # /accounts/login/, which this project does not serve.
        self.assertTrue(response["Location"].startswith(reverse("login")))

    def test_anonymous_post_creates_nothing(self):
        response = self.client.post(reverse("events:create"), event_post_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TutoringEvent.objects.count(), 0)

    def test_anonymous_can_read_the_home_map(self):
        self.assertEqual(self.client.get(reverse("home:index")).status_code, 200)


class OwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.edu", password="pw-for-tests"
        )
        cls.other = User.objects.create_user(
            username="other", email="other@example.edu", password="pw-for-tests"
        )

    def setUp(self):
        self.client.force_login(self.host)

    def test_host_is_taken_from_the_session(self):
        self.client.post(reverse("events:create"), event_post_data())
        self.assertEqual(TutoringEvent.objects.get().host, self.host)

    def test_submitted_host_field_is_ignored(self):
        # The ModelForm has no `host` field, so this must not be honoured.
        self.client.post(
            reverse("events:create"), event_post_data(host=str(self.other.pk))
        )
        self.assertEqual(TutoringEvent.objects.get().host, self.host)

    def test_creating_an_event_redirects_home(self):
        response = self.client.post(reverse("events:create"), event_post_data())
        self.assertRedirects(response, reverse("home:index"))


class NonOwnerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.edu", password="pw-for-tests"
        )
        cls.other = User.objects.create_user(
            username="other", email="other@example.edu", password="pw-for-tests"
        )
        cls.event = TutoringEvent.objects.create(
            title="Calculus II drop-in",
            subject="MAT 2022",
            tutor="Sam",
            date=timezone.now() + timedelta(days=1),
            location="2nd floor study room",
            isPublic=True,
            host=cls.host,
            latitude=ON_CAMPUS[0],
            longitude=ON_CAMPUS[1],
        )

    def test_non_owner_cannot_open_the_edit_form(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("events:edit", args=[self.event.pk]))
        self.assertEqual(response.status_code, 404)

    def test_non_owner_edit_post_changes_nothing(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("events:edit", args=[self.event.pk]),
            event_post_data(title="hijacked"),
        )
        self.assertEqual(response.status_code, 404)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Calculus II drop-in")

    def test_non_owner_cannot_cancel(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("events:cancel", args=[self.event.pk]))
        self.assertEqual(response.status_code, 404)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_cancelled)

    def test_owner_can_edit(self):
        self.client.force_login(self.host)
        self.client.post(
            reverse("events:edit", args=[self.event.pk]),
            event_post_data(title="Calculus II, now in Roux"),
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Calculus II, now in Roux")

    def test_cancel_sets_a_flag_and_keeps_the_row(self):
        self.client.force_login(self.host)
        self.client.post(reverse("events:cancel", args=[self.event.pk]))
        self.event.refresh_from_db()
        self.assertTrue(self.event.is_cancelled)
        self.assertTrue(TutoringEvent.objects.filter(pk=self.event.pk).exists())

    def test_cancel_rejects_get(self):
        # State changes must not happen on GET.
        self.client.force_login(self.host)
        response = self.client.get(reverse("events:cancel", args=[self.event.pk]))
        self.assertEqual(response.status_code, 405)
        self.event.refresh_from_db()
        self.assertFalse(self.event.is_cancelled)


class FormValidationTests(TestCase):
    """The hidden lat/lng inputs are attacker-controlled; the server re-checks."""

    def test_valid_data_is_accepted(self):
        self.assertTrue(TutoringEventForm(data=event_post_data()).is_valid())

    def test_coordinates_outside_the_campus_bbox_are_rejected(self):
        # Lakeland city hall, ~2 km away.
        form = TutoringEventForm(
            data=event_post_data(latitude="28.0395", longitude="-81.9498")
        )
        self.assertFalse(form.is_valid())

    def test_wildly_out_of_range_coordinates_are_rejected(self):
        form = TutoringEventForm(
            data=event_post_data(latitude="91.0", longitude="200.0")
        )
        self.assertFalse(form.is_valid())

    def test_malformed_coordinates_are_rejected(self):
        form = TutoringEventForm(
            data=event_post_data(latitude="not-a-latitude", longitude="")
        )
        self.assertFalse(form.is_valid())

    def test_missing_coordinates_are_rejected(self):
        form = TutoringEventForm(data=event_post_data(latitude="", longitude=""))
        self.assertFalse(form.is_valid())

    def test_a_start_time_in_the_past_is_rejected(self):
        # It would save and then never appear, since the map filters on date.
        form = TutoringEventForm(
            data=event_post_data(
                date=(timezone.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_host_is_not_an_editable_field(self):
        self.assertNotIn("host", TutoringEventForm().fields)

    def test_inactive_buildings_are_not_offered(self):
        retired = CampusLocation.objects.create(
            name="Demolished Hall",
            latitude=ON_CAMPUS[0],
            longitude=ON_CAMPUS[1],
            is_active=False,
        )
        queryset = TutoringEventForm().fields["campus_location"].queryset
        self.assertNotIn(retired, queryset)


class PickerPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.edu", password="pw-for-tests"
        )

    def setUp(self):
        self.client.force_login(self.host)
        self.html = self.client.get(reverse("events:create")).content.decode()

    def test_form_page_renders_the_picker_and_its_data(self):
        self.assertIn('id="campus-map-picker"', self.html)
        self.assertIn('id="map-config"', self.html)
        self.assertIn('id="campus-buildings"', self.html)

    def test_picker_config_carries_the_campus_bbox(self):
        self.assertIn("campus_bbox", self.html)

    def test_csrf_token_is_present(self):
        self.assertIn("csrfmiddlewaretoken", self.html)

    def test_no_external_script_origin_is_used(self):
        for host in ("unpkg.com", "cdnjs.cloudflare.com", "cdn.jsdelivr.net"):
            self.assertNotIn(host, self.html)

    def test_fallback_text_is_server_rendered(self):
        # The building dropdown keeps the form usable with no map.
        self.assertIn("map-picker__fallback", self.html)


class EscapingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.edu", password="pw-for-tests"
        )

    def test_a_hostile_event_title_is_not_rendered_as_markup(self):
        TutoringEvent.objects.create(
            title='<script>alert("xss")</script>',
            subject="MAT 2022",
            tutor="Sam",
            date=timezone.now() + timedelta(days=1),
            location="2nd floor",
            isPublic=True,
            host=self.host,
            latitude=ON_CAMPUS[0],
            longitude=ON_CAMPUS[1],
        )
        html = self.client.get(reverse("home:index")).content.decode()
        self.assertNotIn("<script>alert", html)
