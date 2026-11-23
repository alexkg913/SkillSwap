# Find a Tutor — implementation notes

A student picks a course and a start time; SkillSwap returns tutors who teach
that course and are free for the whole session, and the student books one.

Current state, decisions already made, and what is deliberately not built.

## Shape

| Area | Where |
| --- | --- |
| Course catalog | `tutoring.Course` table, read via `tutoring/catalog.py`; seed in `assets/fsc_courses.json` |
| Models | `tutoring/models.py` |
| Matching query | `tutoring/selectors.py` |
| Validation | `tutoring/forms.py` |
| Views and role rules | `tutoring/views.py` |
| Pages | `tutoring/templates/tutoring/` |
| Account role | `login.User.is_tutor` |

Routes are under `/tutoring/`: `find/`, `book/`, `sessions/`,
`sessions/<pk>/cancel/` for students, and `setup/`, `availability/`,
`availability/<pk>/delete/` for tutors.

## Decisions

**Courses are a table, so they can be added and removed.** `tutoring.Course`
holds `code`, `title`, `level`, and `is_active`. Migration
`0002_course_table` created it, seeded it from `assets/fsc_courses.json`, and
turned the old `course_code` text columns into foreign keys
(`TutorCourse.course`, `TutoringSession.course`) with `to_field="code"`, so
the stored value is still the code. Any stored code the file did not list was
kept as a retired placeholder rather than breaking the constraint.

- **Add** a course in the Django admin, or with `manage.py sync_courses`.
- **Remove** a course by unticking `is_active` (or the "Retire selected
  courses" admin action). A retired course disappears from search, the course
  picker, new offers, and booking -- including a booking from a results page
  loaded before it was retired, which the in-transaction re-check catches.
  Past sessions keep the course and its title. A tutor's offer of a retired
  course stops matching and drops off their list on their next save.
- **Delete** is allowed only while no session references the course
  (`PROTECT`); deleting withdraws any offers of it (`CASCADE`).
- A course's **code is read-only** in the admin after creation: it is what
  offers and sessions store, so changing it would rename history. Add a new
  course and retire the old one instead.

Nothing is cached in-process, so changes take effect on the next request.
`catalog.search_courses` ranks the ~1,000 active rows in Python per request,
which is a few milliseconds; the space-insensitive "MAT2022" match is awkward
to express portably in SQL.

Majors (`login/choices.py`) and skills (`user_profile/skill_catalog.py`) are
still in-code lists; only courses moved to the database.

**Availability is concrete intervals, not recurring rules.** A tutor adds the
specific windows they are free. Recurrence plus daylight saving is where
scheduling code usually goes wrong, and nothing in the MVP needs it.

**Intervals are half-open, `[start_at, end_at)`.** A session ending at 3pm and
another starting at 3pm do not collide, so back-to-back bookings work. This is
the rule behind `selectors.overlapping_sessions`.

**A window must *fully contain* the requested session.** Partial overlap is not
a match: a tutor free 2:00–2:30 cannot take a 2:00–3:00 session.

**Sessions are 60 minutes** (`tutoring.models.SESSION_MINUTES`). The project had
no existing duration policy, so the student UI offers one fixed length and
derives the end time.

**Results identify a tutor by `TutorCourse` id, never by account.** The search
payload carries a display name, major, and course; the booking form submits the
`TutorCourse` primary key and the server resolves the tutor from it. This keeps
`events/selectors.py`'s rule intact — no email (it is the `USERNAME_FIELD`) and
no account UUID reaches a page. Booking re-checks permission regardless.

**Graduate courses are excluded from the pickers.** `forms.TUTORING_COURSE_LEVELS`
limits them to undergraduate plus the two Foundations group entries. Peer
tutoring here is an undergraduate activity.

**The course field is a searchable combobox, not a `<select>`.** ~960 options
is both unusable and about 75 KB of markup per page. `tutoring/courses/`
(`views.course_options`) returns up to 20 ranked matches as JSON and
`static/tutoring/js/course_search.js` drives the listbox, mirroring the skills
picker (`user_profile.views.skill_options` + `skill_search.js`). The submitted
value is a hidden input, so **the server validates every code against the full
allowed active courses regardless of what the page offered** — the search box only
decides what is convenient to pick, never what is permitted. The find page is
now about 3.8 KB.

`catalog.search_courses` ranks a code prefix first, then a title prefix, then a
substring of either, then (for multi-word queries) all tokens appearing
somewhere in the code or title — so "intro to soc" finds `SOC 1100`. Matching
is plain substring work; there is no fuzzy spelling, because course codes are
short and structured and typo tolerance on them produces noise. The skills
catalog does use fuzzy matching, which is right for free-text skill names and
wrong here.

**One role at a time.** `is_tutor` is non-null, defaults false, and existing
accounts migrate to student. A tutor cannot book; a student cannot set courses
or availability. Enforced by `views.tutor_required` / `views.student_required`,
not by which links a template renders.

## Booking is transactional, and the SQLite limit

A search result is informational, never a reservation. `views.book_session`
re-evaluates everything inside `transaction.atomic()`: the tutor is still a
tutor, a window still covers the interval, and no confirmed session overlaps.
On failure the student is redirected back to refreshed results with a `303` and
a concise message — the API equivalent of a `409`.

**The limitation to know about.** SQLite has no exclusion constraints, and
`select_for_update()` is a no-op there, so *arbitrary interval overlap* cannot
be enforced declaratively. What protects the data:

1. the re-checks inside the transaction, which is the normal path;
2. SQLite's database-level write lock, which serialises concurrent writers;
3. a partial `UniqueConstraint` on `(tutor, start_at)` where
   `status = "confirmed"`, which catches two identical confirmed bookings at the
   database level even if application checks are bypassed.

Two bookings that *partially* overlap at different start times are prevented by
(1) and (2), not by a constraint. On PostgreSQL this should become a real
exclusion constraint over a `tstzrange`, at which point (3) is redundant.

## Time handling

`USE_TZ` is on and `TIME_ZONE` is `America/New_York`. Datetimes are entered and
displayed in Eastern and stored as UTC; every page that shows a session time
says "Eastern Time", because a misread time means a missed session.

Local times are parsed by `forms.DateTimeField`, which attaches the active
timezone. A local time that **does not exist** (02:30 on a spring-forward date)
or is **ambiguous** (01:30 on an autumn-back date) is rejected with a form error
rather than guessed at. Booking echoes the chosen time back as ISO 8601 *with a
UTC offset*, so a stale results page cannot shift a session by an hour across a
transition.

## Deliberately not built

Recurring weekly schedules, tutor ranking or recommendation, matching beyond
this filter, payments, video, messaging, ratings, waitlists, notifications, and
external calendar sync. Role switching has no UI: nothing in the MVP needs one,
and adding it requires a policy for tutors who already have booked sessions.

## Known rough edges

- **The course picker needs JavaScript to search.** Without it, each picker
  falls back to a plain text input that accepts one exact course code, so a
  tutor cannot select several courses in one no-JS submission. This matches the
  existing skills picker's trade-off. Validation is unaffected either way.
- **`user_profile.ProfileForm.classes_taken` is declared twice**, so the
  course picker there never renders — the later `CharField` wins. Unrelated to
  tutoring and left alone on purpose: fixing it needs a data migration from
  free text to catalog codes plus a template change.
- `events.TutorListing` is an unused model with its own duplicate-field bug. It
  predates this work and was not touched.
