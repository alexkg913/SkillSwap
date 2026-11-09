import json
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import CampusLocation, TutoringEvent

User = get_user_model()


def json_script_payload(html, element_id):
    """Return the decoded contents of a Django json_script element."""
    match = re.search(
        r'<script id="%s" type="application/json">(.*?)</script>' % re.escape(element_id),
        html,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("No json_script element with id %r in the response." % element_id)
    return json.loads(match.group(1))


class CampusMapRenderTests(TestCase):
    """The home map renders for anonymous visitors; the home page is public."""

    def setUp(self):
        self.response = self.client.get(reverse("home:index"))
        self.html = self.response.content.decode()

    def test_home_page_renders_for_anonymous_visitor(self):
        self.assertEqual(self.response.status_code, 200)

    def test_map_container_is_present_and_labelled(self):
        self.assertIn('id="campus-map"', self.html)
        self.assertIn('role="application"', self.html)
        self.assertIn("aria-label=", self.html)

    def test_fallback_text_is_server_rendered(self):
        # Doubles as the no-JS state, so it must come from the server.
        self.assertIn("map__fallback", self.html)
        self.assertIn("Map loading...", self.html)

    def test_leaflet_is_loaded_from_vendored_static_files(self):
        self.assertIn("home/vendor/leaflet/leaflet.js", self.html)
        self.assertIn("home/vendor/leaflet/leaflet.css", self.html)
        self.assertIn("home/js/campus_map.js", self.html)
        self.assertIn("home/js/campus_map_init.js", self.html)

    def test_no_external_script_origin_is_used(self):
        for host in ("unpkg.com", "cdnjs.cloudflare.com", "cdn.jsdelivr.net"):
            self.assertNotIn(host, self.html)


class CampusMapConfigTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("home:index"))
        self.html = self.response.content.decode()

    def test_config_comes_from_settings(self):
        config = json_script_payload(self.html, "map-config")
        self.assertEqual(config["tile_url"], settings.SKILLSWAP_MAP_TILE_URL)
        self.assertEqual(config["tile_attribution"], settings.SKILLSWAP_MAP_TILE_ATTRIBUTION)
        self.assertEqual(config["center"], list(settings.SKILLSWAP_MAP_CENTER))
        self.assertEqual(config["default_zoom"], settings.SKILLSWAP_MAP_DEFAULT_ZOOM)

    def test_config_satisfies_the_initializer_contract(self):
        config = json_script_payload(self.html, "map-config")
        self.assertEqual(
            sorted(config),
            [
                "center",
                "default_zoom",
                "tile_attribution",
                "tile_referrer_policy",
                "tile_url",
            ],
        )
        latitude, longitude = config["center"]
        self.assertTrue(-90 <= latitude <= 90)
        self.assertTrue(-180 <= longitude <= 180)

    def test_campus_center_lies_inside_the_campus_bbox(self):
        south, west, north, east = settings.SKILLSWAP_CAMPUS_BBOX
        latitude, longitude = settings.SKILLSWAP_MAP_CENTER
        self.assertTrue(south < latitude < north)
        self.assertTrue(west < longitude < east)

    def test_bbox_corners_are_ordered(self):
        south, west, north, east = settings.SKILLSWAP_CAMPUS_BBOX
        self.assertLess(south, north)
        self.assertLess(west, east)

    def test_tile_url_is_https(self):
        # Tiles are fetched by the browser; mixed content would be blocked.
        self.assertTrue(settings.SKILLSWAP_MAP_TILE_URL.startswith("https://"))

    def test_attribution_is_present(self):
        # The OSMF tile usage policy requires attribution.
        self.assertTrue(settings.SKILLSWAP_MAP_TILE_ATTRIBUTION.strip())


class TileReferrerPolicyTests(TestCase):
    """Regression cover for the OSM "403 Access blocked" tile.

    SecurityMiddleware sends Referrer-Policy: same-origin site-wide, which
    strips the Referer from cross-origin tile requests. OSM blocks requests
    that carry a browser User-Agent but no Referer, so the tile layer must
    override the policy for its own <img> elements.
    """

    def setUp(self):
        self.response = self.client.get(reverse("home:index"))
        self.html = self.response.content.decode()

    def test_site_wide_policy_is_still_restrictive(self):
        # If this ever loosens, the override below stops being necessary --
        # but loosening it site-wide is not the fix we chose.
        self.assertEqual(self.response.headers["Referrer-Policy"], "same-origin")

    def test_tile_referrer_policy_is_sent_to_the_client(self):
        config = json_script_payload(self.html, "map-config")
        self.assertEqual(
            config["tile_referrer_policy"],
            settings.SKILLSWAP_MAP_TILE_REFERRER_POLICY,
        )

    def test_tile_referrer_policy_actually_sends_a_referer(self):
        # "no-referrer" and "same-origin" would both reproduce the block.
        sends_referer_cross_origin = {
            "origin",
            "origin-when-cross-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
            "no-referrer-when-downgrade",
            "unsafe-url",
        }
        self.assertIn(
            settings.SKILLSWAP_MAP_TILE_REFERRER_POLICY,
            sends_referer_cross_origin,
        )


class CampusMapEventPayloadTests(TestCase):
    """The pin payload now comes from events.selectors.

    This class previously asserted the payload was an empty list, which held
    only while the events app had no TutoringEvent. The replacement for that
    assertion is test_payload_is_empty_when_there_is_nothing_to_pin below,
    which checks the empty *state* rather than the missing feature.
    """

    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user(
            username="host", email="host@example.edu", password="pw-for-tests"
        )
        # Already present from the seed migration; get_or_create keeps this
        # working whether or not the seed list still carries this building.
        cls.building, _ = CampusLocation.objects.get_or_create(
            name="Roux Library",
            defaults={"latitude": "28.032497", "longitude": "-81.948901"},
        )

    def payload(self):
        response = self.client.get(reverse("home:index"))
        return json_script_payload(response.content.decode(), "map-events")

    def make_event(self, **overrides):
        fields = {
            "title": "Calculus II drop-in",
            "subject": "MAT 2022",
            "tutor": "Sam",
            "date": timezone.now() + timedelta(days=1),
            "location": "2nd floor study room",
            "isPublic": True,
            "host": self.host,
            "campus_location": self.building,
            "latitude": "28.032497",
            "longitude": "-81.948901",
        }
        fields.update(overrides)
        return TutoringEvent.objects.create(**fields)

    def test_payload_is_empty_when_there_is_nothing_to_pin(self):
        self.assertEqual(self.payload(), [])

    def test_public_upcoming_event_becomes_a_pin(self):
        self.make_event()
        payload = self.payload()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["title"], "Calculus II drop-in")
        self.assertEqual(payload[0]["building"], "Roux Library")

    def test_coordinates_are_json_numbers_not_decimal_strings(self):
        # campus_map.js validates with Number.isFinite(), which a string fails,
        # so a Decimal leaking through here would silently blank the map.
        self.make_event()
        pin = self.payload()[0]
        self.assertIsInstance(pin["latitude"], float)
        self.assertIsInstance(pin["longitude"], float)

    def test_pin_payload_exposes_no_private_fields(self):
        self.make_event()
        payload = self.payload()
        self.assertTrue(payload)
        for event in payload:
            for private in ("email", "host", "host_id", "id", "pk"):
                self.assertNotIn(private, event)
            self.assertNotIn(self.host.email, json.dumps(event))
            self.assertNotIn(str(self.host.pk), json.dumps(event))

    def test_cancelled_private_and_past_events_are_not_pinned(self):
        self.make_event(title="cancelled", is_cancelled=True)
        self.make_event(title="private", isPublic=False)
        self.make_event(title="past", date=timezone.now() - timedelta(days=1))
        self.assertEqual(self.payload(), [])

    def test_listings_panel_renders_the_same_events_server_side(self):
        # The map must not be the only way in: the panel is the accessible path.
        self.make_event()
        html = self.client.get(reverse("home:index")).content.decode()
        self.assertIn("Calculus II drop-in", html)
        self.assertIn("Roux Library", html)

    def test_empty_state_is_explicit_in_the_listings_panel(self):
        html = self.client.get(reverse("home:index")).content.decode()
        self.assertIn("No upcoming tutoring events yet.", html)
