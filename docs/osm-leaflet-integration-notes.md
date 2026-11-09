# OSM / Leaflet integration handoff

## Current state

The basemap is **integrated and rendering**, and **event pins are now live**. The home page
loads a vendored Leaflet build, pulls OpenStreetMap raster tiles, centres on the Florida
Southern College campus, and renders a marker per upcoming public tutoring event.
`home.views.map_events()` serves that payload from `events.selectors`.

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
| Tests | `home/tests.py`, `events/tests.py` |
| Pin models | `events/models.py` → `CampusLocation`, `TutoringEvent` pin fields |
| Pin payload | `events/selectors.py` |
| Pin write path | `events/forms.py`, `events/views.py`, `events/urls.py` |
| Picker mode | `campus_map.js` → `initializePicker()`, `events/static/events/js/event_picker_init.js` |
| Event form | `events/templates/events/event_form.html` |

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

1. **Nobody has opened the map in a real browser yet.** This was true before the pins work
   and is still true: the environment it was built in had no browser available, so rendering
   was exercised headlessly (see below). Do this before merging.
2. **The canonical FSC building list.** Built up across three migrations, all sourced from
   OpenStreetMap with each row carrying its OSM way id:

   | Migration | What it does |
   | --- | --- |
   | `0006_seed_campus_locations` | 17 study-plausible buildings, active |
   | `0007_add_weinstein_and_becker` | Weinstein Computer Sciences Center, Becker Business Building |
   | `0008_curate_campus_locations` | adds 7 more as `is_active=False`; retires Allan Spivey Hall and Joseph-Reynolds Hall |

   Current state: **26 rows, 17 offered** in the picker dropdown. Not offered are the three
   Publix Commons, three Student Housing halls, the Admissions Center, Allan Spivey Hall and
   Joseph-Reynolds Hall. Residences that were never seeded at all (Nicholas, Wesley, Miller)
   have no row, which is equivalent for the dropdown.

   Curation is done with `is_active=False`, not deletion: `campus_location` is `PROTECT`, so
   a delete refuses on any building an event references, and deactivation is reversible.

   These are still OSM's names rather than FSC's official ones, and a few were shortened or
   spelling-corrected for the dropdown — `Chatlos Journalism Building` corrects OSM's
   `Wlliam` typo, which was still present upstream as of 2026-10-25. Someone with the
   official campus directory should confirm spellings and flag any study space the list
   misses.
3. **Pre-existing `EventInteraction` schema drift — now known to cause real failures.**
   Migration `0003_eventinteraction` only ever created `id` and `student` (as a `TextField`),
   but the model declares `student` as a FK, plus `tutoring_event` and `status`. The database
   table really does have only `('id', 'student')`. Consequences:
   - `makemigrations --check` has never been clean on `development`; it reports this, not
     the map work.
   - **Deleting any `TutoringEvent` or any `User` raises
     `OperationalError: no such column: events_eventinteraction.tutoring_event_id` /
     `...student_id`**, because both cascade into `EventInteraction`.

   The map pin feature is unaffected (cancelling sets a flag and never deletes), which is why
   the suite passes. The fix is to generate the missing migration — the model is already
   written, so no design decision is needed — but it belongs to whoever owns that model and
   was deliberately left out of `0005_campuslocation_event_pins`.
4. Open decision in `docs/campus-map-plan.md` §11 item 4: whether the README's Google Maps
   badge is dropped. Item 1 (anonymous visibility) is settled — `TutoringEvent.isPublic`
   already existed, so the map filters on it rather than inventing a new rule. Items 2 and 3
   are done.

The README roadmap checkbox stays unchecked until item 1 above is done.

## Verification performed

```sh
.venv/bin/python manage.py check                             # no issues
.venv/bin/python manage.py makemigrations --check --dry-run   # only the pre-existing
                                                              # EventInteraction drift, item 3
.venv/bin/python manage.py test                               # 58 tests, OK
```

Baseline before the pins work was 25 tests; the suite is now 58. `makemigrations --check` was
already reporting the `EventInteraction` drift before any of this landed.

Checked by hand against a local `runserver`:

- Home page 200; every vendored asset, both home scripts and `event_picker_init.js` return 200.
- The `map-events` payload carries real pins with `latitude` / `longitude` as JSON **numbers**,
  and no host email, no primary keys.
- `/events/new/` as an anonymous visitor redirects to `/login/?next=/events/new/` — this
  needed `LOGIN_URL = "login"`, without which Django used its unset default of
  `/accounts/login/`, which this project does not serve. `messaging` had the same latent
  dead redirect and is fixed by the same line.
- End to end as a signed-in host: create redirects home and the pin appears; a POSTed `host`
  field is ignored and ownership comes from the session; an off-campus pin is rejected with a
  visible message and no row; a non-owner cancel returns 404 and leaves the event active; an
  owner cancel sets `is_cancelled`, keeps the row, and removes the pin from the map.

Browser rendering was exercised headlessly by running the real `campus_map.js` in Node against
the live server's `json_script` output with Leaflet stubbed. Confirmed `setView` receives
`[28.030456, -81.945543]` at zoom 16, the attribution survives `json_script` escaping with its
link intact, both pins become markers at their coordinates with full popup text, and a hostile
event title stays inert text (the popup is built with `textContent`, never `innerHTML`). In
picker mode: the marker starts at the campus centre, a map click and a building selection both
write 6-decimal values to the hidden inputs, and dragging off campus raises the advisory
warning while the server still rejects the submission.

Tile serving was re-checked against `https://tile.openstreetmap.org/16/17850/27448.png`:
a browser `User-Agent` **with** a `Referer` returns a real PNG, and **without** one returns
HTTP 200 carrying `x-blocked: Access denied`. That is the documented failure above, and
`SKILLSWAP_MAP_TILE_REFERRER_POLICY` is what avoids it.

**Still not done: nobody has opened the page in a real browser to look at the tiles.** No
browser was available in the environment this was built in. See "Still outstanding" item 1.
