# OSM / Leaflet integration handoff

## Current state

The basemap is **integrated and rendering**. The home page loads a vendored Leaflet build,
pulls OpenStreetMap raster tiles, and centres on the Florida Southern College campus. There
are **no event pins yet** — the `events` app that owns `TutoringEvent` is not on this branch,
so `home.views.map_events()` returns an empty list and the map renders bare.

What is wired up:

| Piece | Location |
| --- | --- |
| Vendored Leaflet 1.9.4 | `home/static/home/vendor/leaflet/` (see its `PROVENANCE.md`) |
| Map settings | `SkillSwap/settings.py`, `SKILLSWAP_MAP_*` / `SKILLSWAP_CAMPUS_BBOX` |
| Server payload | `home/views.py` → `map_config()`, `map_events()` |
| Template | `home/templates/home/index.html` → `#campus-map` + two `json_script` elements |
| Leaflet initializer | `home/static/home/js/campus_map.js` (unchanged contract) |
| Page glue | `home/static/home/js/campus_map_init.js` |
| Styling | `home/static/home/css/style.css` → `.map`, `.map__fallback`, `#campus-map`, Leaflet skin |
| Tests | `home/tests.py` |

## Values in use

Settings live in `SkillSwap/settings.py`. Neither OSM raster tiles nor Leaflet needs an API
key, so there is no secret to manage.

| Setting | Value | Source |
| --- | --- | --- |
| `SKILLSWAP_MAP_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | OSMF standard tile layer; override with the `SKILLSWAP_MAP_TILE_URL` environment variable |
| `SKILLSWAP_MAP_TILE_ATTRIBUTION` | `© <a …>OpenStreetMap</a> contributors` | required by the OSMF tile usage policy; override with `SKILLSWAP_MAP_TILE_ATTRIBUTION` |
| `SKILLSWAP_MAP_TILE_REFERRER_POLICY` | `strict-origin-when-cross-origin` | set on each tile `<img>` so tile requests carry a `Referer`; see the troubleshooting section below before changing it |
| `SKILLSWAP_MAP_CENTER` | `(28.030456, -81.945543)` | centroid of the FSC campus polygon, OpenStreetMap way `113525303`, retrieved 2026-10-01 |
| `SKILLSWAP_MAP_DEFAULT_ZOOM` | `16` | whole campus fits the panel at this zoom |
| `SKILLSWAP_CAMPUS_BBOX` | `(28.0262, -81.9526, 28.0352, -81.9393)` | same OSM polygon (`28.027700..28.033683` by `-81.951084..-81.940791`), padded ~0.0015° (~150 m) |

`SKILLSWAP_CAMPUS_BBOX` is `(south, west, north, east)`. Nothing reads it yet; it exists for
the server-side validation of submitted pins described in `docs/campus-map-plan.md` §7. The
padding is a judgement call — tighten it to the raw polygon if the team would rather reject
pins on bordering sidewalks and parking lots.

Do not move these values into `campus_map.js`. Server-provided configuration keeps deployment
settings out of static code and permits a tile-provider change without touching JavaScript.

### Environment variables

Both are optional; the defaults above apply when unset.

```sh
# Optional: point at a hosted tile provider instead of the OSMF servers.
export SKILLSWAP_MAP_TILE_URL="https://tile.example.net/{z}/{x}/{y}.png"
export SKILLSWAP_MAP_TILE_ATTRIBUTION="© Example Tiles"
```

## Implementation notes worth knowing

- **No inline script.** The glue lives in `campus_map_init.js` rather than a `<script>` block
  in the template, so the page needs no `script-src` exception under a future CSP.
- **Progressive enhancement.** `#campus-map` ships with the `hidden` attribute and
  `.map__fallback` ("Map loading…") is server-rendered. The glue reveals the container and
  hides the fallback; if Leaflet is missing, the JSON is unreadable, or `initialize` throws,
  it reverses that and the fallback explains the map is unavailable. The `.results` listings
  panel beside the map is the keyboard-accessible equivalent of the pins.
- **Vendor path is flattened.** The release archive's `dist/` segment was dropped because the
  repository `.gitignore` ignores `dist/`. `leaflet.css` and `images/` must stay siblings —
  Leaflet finds its default marker icons by reading `.leaflet-default-icon-path` from the
  stylesheet.
- **CSS.** `.map` lost its flex centering (it fought Leaflet's absolutely-positioned panes;
  the centering moved to `.map__fallback`) and its `backdrop-filter` (tiles cover it). It
  gained `overflow: hidden` so tiles clip to the existing `border-radius`. `#campus-map` has
  an explicit height, which Leaflet requires.
- **Template comments.** Use `{% comment %}` for multi-line notes. Django's `{# … #}` is
  single-line only and a multi-line one renders into the page.

## Troubleshooting: "403 Access blocked" tiles

If the map renders but every tile is a grey "Access blocked — App is not following the tile
usage policy of OpenStreetMap's volunteer-run servers: osm.wiki/Blocked" image, OSM is
serving the block tile. It arrives as **HTTP 200 with an `x-blocked` response header**, so
nothing in the browser console looks like an error.

This was hit once already, on 2026-10-01, and the cause was ours:

> Django's `SecurityMiddleware` sends `Referrer-Policy: same-origin` site-wide
> (`SECURE_REFERRER_POLICY`, which has defaulted to `same-origin` since Django 3.1). That
> strips the `Referer` from cross-origin requests, so tile requests arrived carrying a
> browser `User-Agent` with **no `Referer`** — OSM's signature for something impersonating a
> browser — and were blocked.

The fix is `SKILLSWAP_MAP_TILE_REFERRER_POLICY`, which Leaflet puts on each tile `<img>`.
A per-element `referrerpolicy` overrides the document policy for that request only, so the
site-wide `same-origin` policy stays restrictive. **Do not "fix" this by loosening
`SECURE_REFERRER_POLICY` for the whole site.**

Observed behaviour of the block, measured with `curl` against
`https://tile.openstreetmap.org/16/17850/27448.png`:

| Request | Result |
| --- | --- |
| Browser `User-Agent` + any `Referer` | real tile |
| Browser `User-Agent`, no `Referer` | **blocked** |
| No `User-Agent` at all | **blocked** |
| curl's default `User-Agent` | **blocked** |
| `User-Agent: Leaflet/1.9.4` + `Referer` | real tile |

To diagnose a recurrence, check the response headers of a tile request in the browser's
network tab for `x-blocked`, and check whether the request carried a `Referer`. The block is
applied per request at the CDN edge, not as a lasting ban on the IP.

If it turns out to be something we cannot correct — a genuine policy disagreement, or
sustained traffic beyond casual use — the escape hatch is the `SKILLSWAP_MAP_TILE_URL`
environment variable. Point it at a provider whose terms we do meet and update
`SKILLSWAP_MAP_TILE_ATTRIBUTION` to match that provider's required credit. That is the whole
reason the tile URL is a setting rather than a constant in the JavaScript.

## Still outstanding

Everything below is unchanged from the original plan and deliberately **not** built here.

1. The `events` app: `TutoringEvent` / `CampusLocation` models, migrations, forms, permission
   rules, and tests (`docs/campus-map-plan.md` §§5–7, 10). Scaffold is on
   `origin/feature/events`.
2. `events/selectors.py` → the real pin payload for `home.views.map_events()`. Expose public
   fields only: no account emails, no user IDs. The home page is reachable anonymously.
3. The canonical FSC building list for the `CampusLocation` seed migration. Campus centre and
   bbox are now real values; the building names and their coordinates still need collecting.
4. Picker mode in `campus_map.js` for `/events/new/` (draggable marker + building dropdown
   writing to hidden lat/lng inputs), with the bbox re-checked on the server.
5. Open decisions in `docs/campus-map-plan.md` §11: whether anonymous visitors see pins
   (item 1) and whether the README's Google Maps badge is dropped (item 4). Item 2, the
   `America/New_York` timezone switch, is done. Item 3 is partly done, see above.

The README roadmap checkbox stays unchecked: a basemap with no pins is not the map feature.

## Verification performed

```sh
.venv/bin/python manage.py check                          # no issues
.venv/bin/python manage.py makemigrations --check --dry-run  # no changes detected
.venv/bin/python manage.py test                           # 22 tests, OK
```

Also checked by hand against a local `runserver`: the home page returns 200, every vendored
asset and both scripts return 200, both `json_script` elements carry the expected payload, and
`https://tile.openstreetmap.org/16/17850/27448.png` (the centre tile) returns a PNG when the
request carries a `Referer`.

The browser rendering itself was exercised headlessly — `campus_map.js` and
`campus_map_init.js` were run against the live server's `json_script` output with Leaflet
stubbed, confirming `setView` receives `[28.030456, -81.945543]` at zoom 16, the attribution
survives `json_script` escaping with its link intact, a pin becomes a marker at its
coordinates, and a hostile event title stays inert text in the popup. **Nobody has yet opened
the page in a real browser to look at the tiles** — do that before merging.
