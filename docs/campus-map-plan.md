<a id="plan-top"></a>

<div align="center">

  <a href="https://github.com/alexkg913/SkillSwap">
    <img src="../assets/propeller_hat.jpg" alt="SkillSwap Logo" width="110">
  </a>

  <h1 align="center">Campus Map &amp; Event Pins</h1>

  <p align="center">
    Implementation plan for the home-screen map that lets students drop pins for tutoring events.
    <br />
    <br />
    <a href="#2-a-map-api-is-really-three-decisions"><strong>Read the recommendation »</strong></a>
    &middot;
    <a href="#11-decisions-we-still-need-to-make">Open Decisions</a>
    &middot;
    <a href="#10-verification">Verification</a>
  </p>

  ![Status][status-shield]
  ![Leaflet][leaflet-shield]
  ![OpenStreetMap][osm-shield]
  ![Django][django-shield]

</div>

<br />

> [!IMPORTANT]
> **Nothing in this document is implemented yet.** This is a design proposal for review.
> The README roadmap checkbox for map integration stays unchecked until the feature is
> built *and* verified.

| | |
| --- | --- |
| **Status** | Proposed — awaiting team review |
| **Last updated** | 2026-09-30 |
| **Target app** | `events/` (scaffold already exists on `origin/feature/events`) |
| **New Python dependencies** | **None** |
| **New API keys / billing accounts** | **None** |

<br />

<!-- TABLE OF CONTENTS -->

<details>
  <summary>Table of Contents ≽^•⩊•^≼</summary>
  <ol>
    <li><a href="#1-scope">Scope</a></li>
    <li><a href="#2-a-map-api-is-really-three-decisions">A "Map API" Is Really Three Decisions</a></li>
    <li><a href="#3-recommendation-stay-on-osm-via-leaflet">Recommendation: Stay on OSM, via Leaflet</a></li>
    <li><a href="#4-skip-geocoding--use-a-campus-location-list">Skip Geocoding — Use a Campus Location List</a></li>
    <li><a href="#5-data-model">Data Model</a></li>
    <li><a href="#6-read-path--pins-on-the-home-map">Read Path — Pins on the Home Map</a></li>
    <li><a href="#7-write-path--dropping-a-pin">Write Path — Dropping a Pin</a></li>
    <li><a href="#8-csstemplate-details-that-will-bite">CSS/Template Details That Will Bite</a></li>
    <li><a href="#9-files-touched">Files Touched</a></li>
    <li><a href="#10-verification">Verification</a></li>
    <li><a href="#11-decisions-we-still-need-to-make">Decisions We Still Need to Make</a></li>
  </ol>
</details>

<br />

---

## 1. Scope

The README lists Google Maps under **Future Features**, and `AGENTS.md` says not to build
future features unasked. This work was explicitly requested, so it is in scope — but the
blast radius stays small on purpose.

**In scope**

- [ ] Render existing tutoring events as pins on the home-screen map
- [ ] Let a signed-in student create an event by dropping a pin
- [ ] Edit / cancel an event you host

**Explicitly _not_ in scope**

- Full scheduling system, RSVPs, or attendance
- Ratings, reviews, or in-app messaging on events
- Canvas or Slack involvement
- Any change to the login / profile flows

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 2. A "Map API" Is Really Three Decisions

These get bundled together in conversation, but the right answer differs for each.

| # | Concern | Needs a key / billing? | Decision |
| :-: | --- | :-: | --- |
| 1 | **Basemap tiles** — the picture under the pins | depends on provider | Leaflet + OpenStreetMap raster tiles |
| 2 | **Pin data** — our own events | ❌ no, it's our database | Server-rendered JSON, no new API layer |
| 3 | **Geocoding** — address → lat/lng | usually yes, or rate-limited | **Skip entirely for v1** |

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 3. Recommendation: Stay on OSM, via Leaflet

The original OSM instinct is the right call. Here's the comparison that got us there.

| Option | Size | License | Key / billing | Verdict |
| --- | --- | --- | --- | --- |
| **Leaflet + OSM raster** | ~45 KB | BSD-2-Clause | none | ✅ **Recommended** |
| MapLibre GL JS | ~800 KB + WebGL | BSD-3-Clause | yes, in practice | Nicer rendering, more moving parts |
| Google Maps JS API | — | proprietary | **billing account required** | ❌ Overhead + bill risk |
| Mapbox GL JS | ~800 KB | proprietary (v2+) | yes | ❌ No advantage over MapLibre here |

### Why Leaflet wins for us

- **Zero credentials.** `AGENTS.md` requires that we never commit tokens and that we read
  secrets from environment variables. The easiest way to satisfy that rule is to have no
  secret at all.
- **Google Maps needs a billing account attached** to a Google Cloud project even inside
  the free tier, and its browser key is necessarily public — it has to be referrer-locked
  to be safe. That is real admin overhead and a real "oops, we got charged" risk for a
  four-person class project. The badge in our README is a logo, not a commitment.
- **MapLibre is lovely and overkill.** Vector tiles for roughly twenty pins on one campus
  does not justify 800 KB and a tile-provider account.

### One honest caveat about OSM's tile servers

The OSMF tile usage policy requires attribution and is explicitly **not** for heavy use or
large user bases. For development and a class demo we are comfortably inside casual use.

We mitigate by making the tile URL a single Django setting, so switching to a hosted
provider later is a config change rather than a code change:

```python
# SkillSwap/settings.py
SKILLSWAP_MAP_TILE_URL = os.environ.get(
    "SKILLSWAP_MAP_TILE_URL",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
)
SKILLSWAP_MAP_TILE_ATTRIBUTION = "© OpenStreetMap contributors"

SKILLSWAP_MAP_CENTER       = (28.0300, -81.9490)                  # ← verify, see §11
SKILLSWAP_MAP_DEFAULT_ZOOM = 16
SKILLSWAP_CAMPUS_BBOX      = (28.024, -81.956, 28.036, -81.942)   # ← verify, see §11
```

> [!TIP]
> **Vendor Leaflet into `events/static/events/vendor/leaflet/` instead of using a CDN.**
> Development keeps working offline, the version is pinned, and we avoid a third-party
> script origin — which matters if we add a Content-Security-Policy for the OWASP ASVS
> work the README commits us to.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 4. Skip Geocoding — Use a Campus Location List

Nominatim (OSM's geocoder) caps us at one request per second, requires an identifying
User-Agent, and its policy **forbids autocomplete-style use** — which is exactly what a
"type the building name" box would be. Paid geocoders bring back the API-key problem.

For a single-campus app a geocoder is the wrong tool anyway. Instead we seed a
`CampusLocation` table with FSC buildings, and the host either **picks a building** or
**clicks the map to drop a free pin**.

- No second external dependency, no rate limits, no key.
- Better UX — "Christoverson Library" beats a text search that might match a library in Ohio.
- Satisfies the `AGENTS.md` rule that core local workflows stay usable during external API
  failures: if the tile server is down, the map degrades to a dropdown and the form still submits.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 5. Data Model

Both models live in `events/models.py`.

```python
CampusLocation
    name             CharField(120, unique=True)
    latitude         DecimalField(max_digits=9, decimal_places=6)
    longitude        DecimalField(max_digits=9, decimal_places=6)
    is_active        BooleanField(default=True)

TutoringEvent
    host             FK(settings.AUTH_USER_MODEL, PROTECT, related_name="hosted_events")
    title            CharField(140)
    course_code      CharField(20, blank=True)      # reused later for search/filter
    description      TextField(blank=True)
    starts_at        DateTimeField()
    ends_at          DateTimeField()
    campus_location  FK(CampusLocation, null=True, blank=True, on_delete=PROTECT)
    latitude         DecimalField(max_digits=9, decimal_places=6)   # the pin itself
    longitude        DecimalField(max_digits=9, decimal_places=6)
    location_note    CharField(140, blank=True)     # "2nd floor study room"
    is_cancelled     BooleanField(default=False)
    created_at       DateTimeField(auto_now_add=True)
    updated_at       DateTimeField(auto_now=True)
```

### Design points, each with a reason

<table>
<tr><th align="left">Choice</th><th align="left">Why</th></tr>
<tr>
<td><b>No GeoDjango / PostGIS</b></td>
<td>It would force Postgres plus GDAL/GEOS system libraries onto a project with three
dependencies on SQLite. Two decimal columns are the correct tool at campus scale.</td>
</tr>
<tr>
<td><b><code>max_digits=9, decimal_places=6</code></b></td>
<td>~0.11 m precision, and fits both <code>28.030000</code> and <code>-81.949000</code>.</td>
</tr>
<tr>
<td><b>Event stores its own lat/lng</b><br>even when a building is chosen</td>
<td>Keeps the map query single-table, and relocating a building later doesn't silently
move every past event that referenced it.</td>
</tr>
<tr>
<td><b>DB-level constraints</b></td>
<td><code>AGENTS.md</code> asks for persistent invariants in the database:
<code>CheckConstraint(ends_at__gt=starts_at)</code>, latitude in [-90, 90],
longitude in [-180, 180].</td>
</tr>
<tr>
<td><b>Indexes on <code>starts_at</code> and <code>(is_cancelled, starts_at)</code></b></td>
<td>The home map has exactly one query: "upcoming, not cancelled."</td>
</tr>
</table>

**Known tradeoff:** plain decimal columns mean "events within 500 m" becomes a
bounding-box filter in the ORM rather than a spatial index lookup. Irrelevant at
tens-of-events scale; worth revisiting only if we ever go multi-campus.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 6. Read Path — Pins on the Home Map

The home view stays a plain Django view. **No new JSON endpoint for v1.** We serialize the
same queryset the listings panel already uses straight into the template:

```django
{{ map_config|json_script:"map-config" }}
{{ map_events|json_script:"map-events" }}
```

`events/static/events/js/campus_map.js` reads both elements and initializes Leaflet.

### Why `json_script` instead of a fetch endpoint

- Zero new URLs — nothing new to authorize, rate-limit, or CSRF-protect.
- The map and the listings panel physically cannot disagree; they're one queryset.
- `json_script` escapes safely, so a user-supplied event title can't become an XSS vector.

A real `events/map.json` endpoint is the natural **step 2**, once the (currently dead)
search bar needs to re-filter without a page reload. The JS contract stays identical, so
that change is purely additive.

### Layering

Query logic goes in `events/selectors.py`, not the view — `AGENTS.md` wants views focused on
request handling.

```python
upcoming_events_for_map()   # .select_related("campus_location") to avoid N+1
map_config()                # tile URL, attribution, center, zoom, bbox
```

> [!WARNING]
> **Serialize only public fields.** Title, course code, building name, start/end,
> location note, and the host's *display name*. Never `host.email`, never the host UUID.
> The home page is reachable without logging in.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 7. Write Path — Dropping a Pin

A separate page at `/events/new/`, wired to the **existing dead "Create a Tutoring Event"
nav link** — not a modal on the home page. It reuses the same Leaflet module in "picker" mode.

```
@login_required
   │
   ├─ map with a draggable marker  ─┐
   ├─ CampusLocation dropdown      ─┤──→ updates hidden latitude / longitude inputs
   │                                │
   └─ POST ──→ TutoringEventForm ──→ server-side validation ──→ redirect to home
```

### Non-negotiables, all traceable to `AGENTS.md`

| Rule | Implementation |
| --- | --- |
| Assign ownership from the authenticated user | `host` comes from `request.user`; the ModelForm's `fields` list never includes it |
| Validate input on the server | Re-check lat/lng against `SKILLSWAP_CAMPUS_BBOX` — the hidden inputs are attacker-controlled, and browser-side map bounds prove nothing |
| Non-GET for state changes, CSRF preserved | POST + `{% csrf_token %}` on create / edit / cancel; GET never mutates |
| Object-level permissions | Edit and cancel check `event.host_id == request.user.id`, not merely "is authenticated" |
| Don't delete data | Cancel sets `is_cancelled`; it is not a row delete |
| Timezone-aware datetimes | See below |

### Timezone

We currently run `TIME_ZONE = "UTC"` with `USE_TZ = True`, and events are the first
time-bearing feature in the project. **Recommendation: switch `TIME_ZONE` to
`"America/New_York"` and label times "ET" in the UI.** The database still stores UTC —
this only affects display — and a campus event advertised as "14:00 UTC" is actively
misleading to a student reading it.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 8. CSS/Template Details That Will Bite

Findings from reading `home/static/home/css/style.css` and `home/templates/home/index.html`:

- **`.map` currently sets `display: flex; align-items: center; justify-content: center`** to
  center the "Map loading…" text. That centering fights Leaflet's absolutely-positioned
  panes. Scope it to the placeholder state instead of the container.
- **Leaflet needs an explicit container height.** The existing `min-height: 420px` works —
  add `overflow: hidden` so tiles clip to the current `border-radius: 20px`.
- **Drop `backdrop-filter` on `.map`** once tiles cover it; it costs compositing for nothing.
- **Keep the Frutiger Aero look** by skinning Leaflet's popup and zoom controls with the
  existing `--glass-white` / `--glass-border` tokens, rather than importing a new visual language.

### Accessibility

> [!CAUTION]
> A canvas full of markers is not keyboard-operable. The map must not be the only way in.

- The `.results` panel beside the map renders the same events server-side, as real links,
  so the map is an *enhancement*.
- Give the map container `role="application"` and an `aria-label`.
- The existing "Map loading…" text doubles as the no-JS fallback.
- Handle the empty state explicitly: zero upcoming events → map still renders, listings
  show a plain-language message.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 9. Files Touched

> The `events` app scaffold and its `INSTALLED_APPS` entry already exist on
> `origin/feature/events`. We build there — **no new Django app.**

```
events/
├── models.py                          TutoringEvent, CampusLocation
├── forms.py                     NEW   TutoringEventForm (bbox + time validation)
├── selectors.py                 NEW   upcoming_events_for_map(), map_config()
├── views.py                           create / edit / cancel
├── urls.py                      NEW   + include() from SkillSwap/urls.py
├── admin.py                           register both models
├── tests.py                           see §10
├── migrations/
│   ├── 0001_initial.py          NEW
│   └── 0002_seed_locations.py   NEW   data migration, FSC buildings
├── static/events/
│   ├── js/campus_map.js         NEW   render mode + picker mode
│   └── vendor/leaflet/          NEW   vendored v1.9.x
└── templates/events/
    └── event_form.html          NEW

home/
├── views.py                           pass map_config + map_events
├── templates/home/index.html          replace .map placeholder, wire nav link
└── static/home/css/style.css          .map adjustments + Leaflet skin

SkillSwap/settings.py                  map settings, "events" in INSTALLED_APPS
README.md                              setup notes (roadmap checkbox stays unchecked)
AGENTS.md                              record the events path + these map decisions
```

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 10. Verification

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test
```

`manage.py check` passes clean on `main` today, so that is a valid baseline to compare against.

### Test coverage, mapped to the `AGENTS.md` checklist

| Area | Test |
| --- | --- |
| Anonymous access | Anonymous GET of home renders pins; anonymous POST to create redirects to login |
| Ownership | Authenticated create assigns `host = request.user` **even when a different `host` is POSTed** |
| Unauthorized access | Non-owner edit/cancel returns 403/404, never success |
| Invalid input | Out-of-bbox and malformed lat/lng rejected; `ends_at <= starts_at` rejected |
| Data exposure | Map payload contains no host email and no host UUID |
| Empty states | Zero upcoming events → map renders, listings show an explicit message |

> [!NOTE]
> **No external-API mocking is needed.** Tiles are fetched by the browser, so the test
> suite never touches the network. That's a concrete benefit of this design over a
> server-side geocoder, which would have required mocked HTTP, timeout handling, and
> rate-limit handling to satisfy `AGENTS.md`.

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

## 11. Decisions We Still Need to Make

<table>
<tr><th>#</th><th align="left">Question</th><th align="left">Recommendation</th></tr>

<tr>
<td align="center"><b>1</b></td>
<td><b>Are event pins visible to anonymous visitors?</b><br>
The home page is public today.</td>
<td><b>Yes, with reduced detail</b> — no host email, host first name only. A
tutoring-discovery map that shows nothing until you log in is far less useful. Easy to
gate behind <code>@login_required</code> instead if the team disagrees.</td>
</tr>

<tr>
<td align="center"><b>2</b></td>
<td><b>Switch <code>TIME_ZONE</code> to <code>America/New_York</code>?</b></td>
<td><b>Yes.</b> One line, display-only, affects the whole project rather than just events —
so it deserves a group nod.</td>
</tr>

<tr>
<td align="center"><b>3</b></td>
<td><b>Campus coordinates and the building list.</b></td>
<td>The center and bbox values in §3 are <b>placeholders</b>. Someone should pull real
coordinates and the canonical FSC building names for the seed migration.</td>
</tr>

<tr>
<td align="center"><b>4</b></td>
<td><b>Does anyone object to dropping the Google Maps badge</b> from the README's
integration list?</td>
<td>Either remove it or demote it to a "someday" note, so the README reflects what we
actually build.</td>
</tr>

</table>

<p align="right">(<a href="#plan-top">back to top</a>)</p>

---

<div align="center">

**Questions or objections?** Leave them on the PR, or grab whoever drafted this.

<sub>Drafted 2026-09-30 · reviewed against <code>AGENTS.md</code> and the current <code>main</code></sub>

</div>

<!-- ================================================================================ -->
<!-- REFERENCE LINKS -->
<!-- ================================================================================ -->

[status-shield]: https://img.shields.io/badge/Status-Proposed-FFA500?style=for-the-badge
[leaflet-shield]: https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white
[osm-shield]: https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white
[django-shield]: https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white
