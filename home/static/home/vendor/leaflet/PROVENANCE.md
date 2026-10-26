# Vendored Leaflet

| | |
| --- | --- |
| Version | 1.9.4 (pinned) |
| License | BSD-2-Clause — see `LICENSE` |
| Source | `https://github.com/Leaflet/Leaflet/releases/download/v1.9.4/leaflet.zip` |
| Retrieved | 2026-10-01 |

## Checksums

Release archive:

```
aaec1d5c3239a613a53e996087629aca1483cb2f0438b11b8a335c6cede4c16b  leaflet.zip
```

Files kept from the archive's `dist/` directory:

```
85d455b4522415f6badc42a0e7d17c919d100347d6b8958bd0dc738fdecd6d50  leaflet.js
a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6  leaflet.css
```

## Notes

- Vendored rather than loaded from a CDN so the version is pinned, development works
  offline, and no third-party script origin has to be allowed by a future
  Content-Security-Policy. See `docs/campus-map-plan.md` §3.
- The archive's `dist/` path segment is deliberately flattened away: the repository
  `.gitignore` ignores `dist/`, so a `vendor/leaflet/dist/` layout would not be committed.
- `leaflet.css` and `images/` must stay siblings. Leaflet locates its default marker
  icons by reading the `background-image` of `.leaflet-default-icon-path` from
  `leaflet.css`, which resolves `images/marker-icon.png` relative to the stylesheet.
- Source maps and the ES-module build were not vendored; only the files the page loads.

To upgrade, replace these files from a new pinned release and update this file.
