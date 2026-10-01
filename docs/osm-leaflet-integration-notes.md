# OSM / Leaflet integration handoff

## Current state

The map is **not integrated**. No template loads Leaflet or the staging module, no Django
settings were added, and the home view does not send map data. Consequently, the application
makes no request to OpenStreetMap or another tile provider.

`home/static/home/js/campus_map.js` is an inert, reusable Leaflet initializer prepared for
later use. It deliberately has no campus, zoom, bounds, tile URL, attribution, or event-data
defaults. It runs only when a future template explicitly calls
`window.SkillSwapCampusMap.initialize(...)`.

## Values for the team to provide

Enter the following values only when approving the actual integration. The names below are
suggested locations, based on `docs/campus-map-plan.md`; they do not exist in the code yet.

| Value | Add it in | Used by |
| --- | --- | --- |
| Tile URL | `SkillSwap/settings.py` as `SKILLSWAP_MAP_TILE_URL` | `home/views.py` → `tileUrl` |
| Tile attribution text | `SkillSwap/settings.py` as `SKILLSWAP_MAP_TILE_ATTRIBUTION` | `home/views.py` → `tileAttribution` |
| Campus center `[latitude, longitude]` | `SkillSwap/settings.py` as `SKILLSWAP_MAP_CENTER` | `home/views.py` → `center` |
| Initial zoom | `SkillSwap/settings.py` as `SKILLSWAP_MAP_DEFAULT_ZOOM` | `home/views.py` → `zoom` |
| Campus bounding box | `SkillSwap/settings.py` as `SKILLSWAP_CAMPUS_BBOX` | future event form validation and picker mode |
| Canonical campus buildings and coordinates | future `events` data migration or admin-managed `CampusLocation` records | future event form and map pins |
| Pin payload | future `events/selectors.py` | `home/views.py` → `events` |

Do not put these values in `campus_map.js`; server-provided configuration keeps deployment
configuration out of static code and permits later tile-provider changes without changing JS.

## Activation checklist

1. Vendor a reviewed, pinned Leaflet release under
   `home/static/home/vendor/leaflet/` (or the eventual `events` static directory), including
   its JavaScript, CSS, and marker image assets. Do not use an unpinned CDN.
2. Add the five map settings above in `SkillSwap/settings.py`. The tile URL may read from an
environment variable, but neither OSM raster tiles nor Leaflet need an API key.
3. In `home/views.py`, build a `map_config` dictionary from those settings and obtain the
   public event-pin payload. Do not expose account emails, IDs, or other private profile data.
4. In `home/templates/home/index.html`, replace the existing map placeholder with a labeled
   map container, include Leaflet's CSS/JS and `home/js/campus_map.js`, then pass the
   server data with Django `json_script`. Call `initialize` only after those scripts and
   data elements are present.
5. In `home/static/home/css/style.css`, give the active map container an explicit height and
   `overflow: hidden`; do not retain the current flex-centering placeholder rules on the
   Leaflet container.
6. Build the events app, form validation, permission rules, and tests described in
   `docs/campus-map-plan.md` before allowing students to create pins.

## Required initializer contract

After activation, call the staging module with every field below:

```js
window.SkillSwapCampusMap.initialize({
  element: document.getElementById("campus-map"),
  tileUrl: mapConfig.tile_url,
  tileAttribution: mapConfig.tile_attribution,
  center: mapConfig.center,
  zoom: mapConfig.default_zoom,
  events: mapEvents,
});
```

`center` and each event coordinate are `[latitude, longitude]`. Each event requires
`title`, `latitude`, and `longitude`; `location_note` is optional. Popup text is inserted
with `textContent`, not HTML, so event titles cannot execute markup.
