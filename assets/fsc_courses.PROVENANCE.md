# Course catalog provenance

`fsc_courses.json` holds 1,174 Florida Southern College course codes and titles,
extracted from the **FSC Academic Catalog 2026/2027** course-description
sections: undergraduate (catalog pages 205-382) and graduate (383-433). It
supersedes the 74-entry WRIGHT Foundations list that was previously inlined in
`user_profile/forms.py`; 71 of those 74 are present here under the same codes,
and the three that are not are explained below.

**This file is a seed, not the live catalog.** Courses live in the
`tutoring.Course` table: migration `tutoring/0002_course_table` loaded this
file once, and courses are added or retired in the Django admin after that.
Editing this file changes nothing until it is synced (see *Regenerating*).
Application code reads courses through `tutoring/catalog.py`, never by parsing
this file.

## Structure

Each entry has a `code`, a `title`, and a `level`:

| `level` | Count | Meaning |
| --- | --- | --- |
| `undergraduate` | 956 | Undergraduate course descriptions |
| `graduate` | 216 | Graduate course descriptions (DPT, MBA, MSN, EdD, ...) |
| `foundation_group` | 2 | A Foundations requirement met by any course in a group |

## Extraction decisions

- **Cross-listed courses appear once per canonical code.** The catalog
  describes `BIO 3362` and `CHE 3362` as separate entries, each carrying a
  "Same as" note, so both are included and the combined `BIO/CHE 3362` spelling
  used in the degree-requirement tables is not. The old Foundations entry
  `REL/PHI 2219` is therefore represented here as `REL 2219` and `PHI 2219`.
- **`MUS XXXX - Ensemble` and `MUS XXXX - Performance`** are the two
  `foundation_group` entries. They are not real course numbers; they are
  Foundations requirements satisfied by any ensemble or performance course, and
  they are kept because the Foundations list offered them.
- **Titles are title-cased from the catalog's all-caps headings**, preserving
  acronyms (`SCUBA`, `ESOL`, `GIS`, `STEM`, `VITA`, `IPCE`, `AGPC`, `CFA`,
  `CPA`, `DNP`, `FNP`, `VR`, `AI`, `HR`, `US`, `U.S.`, `D.C.`, `K-12`) and
  roman numerals. Where a title differed between the Foundations list and the
  catalog, the catalog's wording wins as the newer, authoritative source --
  for example `PSY 1879` is "From Aristotle to AI: Global Transformations
  Within Psychological Science" rather than the shorter Foundations phrasing.
- Codes are stable identifiers and are what gets stored. Titles are display
  text; rewording one must not require a data migration.

## Regenerating

The source PDF is not committed -- it is 6 MB and is published by the college.
To refresh for a new academic year, download the catalog, extract the text of
the two course-description sections, and rebuild the JSON so that each
all-caps `CODE TITLE` heading becomes one entry, joining headings that wrap
across lines. Then check that the count moved in a direction you expect, and
load it into the database:

```sh
python manage.py sync_courses                   # add new codes, refresh titles
python manage.py sync_courses --retire-missing  # also retire dropped courses
```

`sync_courses` never deletes a course and never re-activates one retired in
the admin. Run `python manage.py test tutoring` afterwards.

A course code in this file is a catalog listing. It is not evidence that a
student completed the course, nor that they are qualified to tutor it.
