import json
import re

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


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
    def setUp(self):
        self.response = self.client.get(reverse("home:index"))
        self.html = self.response.content.decode()

    def test_pin_payload_is_an_empty_list_until_the_events_app_lands(self):
        self.assertEqual(json_script_payload(self.html, "map-events"), [])

    def test_pin_payload_exposes_no_private_fields(self):
        payload = json_script_payload(self.html, "map-events")
        for event in payload:
            self.assertNotIn("email", event)
            self.assertNotIn("host_id", event)
            self.assertNotIn("id", event)
