# AGENTS.md

## Purpose and scope

This file guides coding agents working in the SkillSwap repository. It applies throughout the repository unless a more specific AGENTS.md provides additional local guidance. Follow the user's task instructions and preserve unrelated work.

SkillSwap is an experimental Django web application connecting Florida Southern College students with peer tutoring opportunities. Students should be able to discover tutoring resources, offer help for courses they have completed, and request tutoring sessions.

Read README.md before making changes. The README describes project intent and planned features; it does not prove that a feature already exists. Inspect the actual code, configuration, migrations, and tests before deciding how to implement a task.

## Product priorities

Prioritize the MVP described in the README:

- User authentication and student profiles.
- Tutor and skill listings.
- Search and filtering by course or subject.
- Basic skill matching.
- Session requests.
- Canvas integration.

Ratings, reviews, advanced availability matching, course-focused tutoring hubs, Google Maps, in-app messaging, notifications, gamification, and recommendations are future features. Do not build them unless the current task requests them.

The README also mentions scheduling and campus tutoring events. Keep implementations aligned with the requested scope; do not interpret a session request as permission to build a complete scheduling system.

## Architecture and open decisions

Python and Django are the established backend technologies. The README describes three application responsibilities:

| Area | Responsibility |
| --- | --- |
| Student/Tutor Accounts | Authentication, profiles, and account management. |
| Events | Tutor listings, tutoring events, search, and filtering. |
| In-App Messaging | Communication between tutors and students; a future feature. |

These are conceptual boundaries, not confirmed directory or package names. Reuse the repository's actual application structure rather than creating duplicate apps to match this table.

- The database and frontend are TBD in the README. Inspect the repository for decisions made since the README was written.
- Follow the existing stack and dependency management. Do not introduce a frontend framework, REST framework, database migration, task queue, or real-time messaging service for an unrelated task.
- If a task requires a decision that remains open, explain the tradeoff and clarify consequential choices. Resolve small, reversible implementation details using existing conventions.
- Canvas is an MVP integration. Google Maps is a future feature. Slack is listed as a possible API integration but has no defined behavior or MVP requirement.

### Campus map

The home-page basemap is implemented and rendering; event pins are not. Decisions already
made, so they do not need relitigating:

- **Leaflet 1.9.4 with OpenStreetMap raster tiles, not Google Maps.** No API key, no billing
  account. Leaflet is vendored and pinned under `home/static/home/vendor/leaflet/`; do not
  replace it with a CDN link. See `home/static/home/vendor/leaflet/PROVENANCE.md`.
- **Map configuration lives in settings**, as `SKILLSWAP_MAP_*` and `SKILLSWAP_CAMPUS_BBOX`,
  and reaches the page through `home.views.map_config()` and `json_script`. Do not hardcode
  campus coordinates or tile URLs in JavaScript.
- **No geocoder.** Buildings come from a seeded `CampusLocation` list, not Nominatim, whose
  policy forbids autocomplete-style use.
- `home.views.map_events()` returns an empty list until the `events` app lands. When it does,
  serialize public fields only; the home page is reachable anonymously.
- Current state, values in use, and what remains: `docs/osm-leaflet-integration-notes.md`.
  Full design rationale: `docs/campus-map-plan.md`.

## Working process

1. Read applicable instructions, inspect the working tree, and identify the code related to the request.
2. Check dependency files, settings, existing tests, and CI configuration for the supported environment and commands.
3. Make the smallest coherent change that fully handles the task. Avoid unrelated refactoring, formatting, or dependency upgrades.
4. Update tests and documentation when behavior or setup changes.
5. Run relevant checks and inspect the final diff for accidental changes or secrets.
6. Report what changed, what was verified, and any unresolved limitations.

Do not overwrite another contributor's work, reset the working tree, rewrite shared history, delete data, or deploy changes without authorization. Do not claim a command passed unless it ran successfully.

## Django implementation conventions

- Follow the codebase's naming, formatting, and application patterns. Prefer clear, conventional Django code over elaborate abstractions.
- Use Django authentication and password handling. Reference users through the configured user model rather than assuming a particular implementation.
- Keep views focused on request handling. Put reusable business rules in the existing application layer, and enforce persistent invariants with suitable model or database constraints.
- Validate input on the server using the repository's established forms or serializers. Browser validation alone is insufficient.
- Restrict editable fields explicitly. Assign ownership from the authenticated user rather than trusting a submitted user ID.
- Enforce object-level permissions for profiles, listings, session requests, and any future messages. Authentication alone does not establish ownership or participation.
- Make session-request transitions explicit and validate who may perform them. Use transactions where a change must update multiple records consistently.
- Generate and commit migrations for model changes. Review their effect on existing data; do not rewrite applied migrations casually.
- Inspect query behavior when listing related objects. Use appropriate related-object loading and pagination as the implementation requires.
- Keep basic matching understandable and deterministic. Do not introduce machine learning or infer student qualifications from unavailable data.
- Use timezone-aware datetimes for scheduling. State the displayed timezone wherever ambiguity would affect a session.

## Integrations and student data

- Isolate external API calls in the repository's integration layer so application behavior can be tested without live services.
- Read credentials and service configuration from environment variables or the existing secrets mechanism. Document required variable names with safe placeholders.
- Never commit tokens, passwords, real student records, or credential-bearing configuration. Do not include them in logs, fixtures, screenshots, or error reports.
- Treat Canvas data as private student data. Request and retain only what the feature needs; enforce access controls for imported information.
- Do not treat Canvas enrollment or course access as proof that a student completed a course or is qualified to tutor it.
- Follow the authentication flow and institutional access available to the project. Do not assume FSC provides administrative API access or a particular OAuth configuration.
- Apply timeouts, handle authentication failures and rate limits, and follow pagination when retrieving collections. Avoid unsafe retries of requests that create or modify external records.
- Validate configurable API destinations and avoid sending credentials to arbitrary hosts. Do not scrape Canvas or bypass its access controls.
- Keep core local workflows usable during external API failures where practical. Distinguish unavailable or stale external data from an empty result.
- Mock integrations in automated tests. Live API checks must be explicitly requested and use authorized credentials and data.

## Security expectations

The README identifies NIST SSDF, OWASP ASVS, and Django security guidance as development references. Apply relevant controls; do not claim compliance or certification without supporting evidence.

- Preserve CSRF protection for cookie-authenticated requests. Use POST or another appropriate non-GET method for state changes.
- Preserve template escaping. Do not mark user-generated content safe without a justified sanitization approach.
- Prefer the Django ORM and parameterized queries. Never construct SQL from untrusted input.
- Check authorization before exposing or modifying another student's data. Public listings should expose only information intended to be public.
- Keep production secrets out of source control. Production settings must disable debug output and configure allowed hosts and transport/session security appropriately.
- Return useful errors without exposing credentials, internal configuration, or private data.

## User interface

- Follow the existing frontend conventions and styling.
- Use accessible labels, keyboard-operable controls, clear validation messages, and readable layouts on phones and desktops.
- Handle empty search results, missing profiles, permission failures, and integration outages explicitly.
- Make listing ownership and session-request status clear to students.
- Keep user-facing language simple and avoid implying official FSC endorsement or guaranteed tutor qualifications.

## Verification

Use the repository's documented commands and CI checks first. If it is a standard Django project with manage.py, the following are starting points, using the repository's configured Python environment:

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Run these only when the project structure and dependencies support them. Use the established test runner if the repository uses something else. Never run tests against a production database.

For behavior changes, add meaningful coverage for the affected rules, especially:

- Anonymous access, ownership, and unauthorized access to another user's objects.
- Invalid input and invalid session-request transitions.
- Search, filtering, and matching behavior.
- External API failures, missing credentials, and pagination where relevant.
- Migration behavior when data preservation is material to the change.

Run existing formatting and lint checks when configured. For UI changes, verify the affected flow and relevant empty/error states. If a check cannot run, state the command and blocker instead of reporting success.

## Documentation and handoff

- Update setup instructions when dependencies, environment variables, migrations, or startup steps change.
- Keep implemented functionality distinct from planned features. Update README roadmap items only when the feature is complete and verified.
- Keep this file current as database, frontend, application paths, and test commands become established.
- Finish with a concise description of the resulting behavior, verification results, and any remaining setup or decisions.
