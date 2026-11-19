"""Load ``assets/fsc_courses.json`` into the ``Course`` table.

The database is the source of truth for courses; the JSON file is only the
seed and the input for a yearly catalog refresh. Used by migration 0002 and by
``manage.py sync_courses``.

This module deliberately imports no models. The migration passes its
historical ``Course`` model in, so the seed keeps working however the real
model changes later.
"""

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent.parent / "assets" / "fsc_courses.json"

LEVELS = {"undergraduate", "graduate", "foundation_group"}


def read_catalog_file(path=CATALOG_PATH):
    """Return ``[(code, title, level), ...]`` from a catalog JSON file.

    File order is kept. Duplicate codes keep their first entry rather than
    silently overwriting one another. Raises ``ValueError`` on an entry with
    no code or title or an unknown level, because loading half a bad file is
    worse than loading none of it.
    """
    with Path(path).open(encoding="utf-8") as catalog:
        data = json.load(catalog)

    seen = set()
    entries = []
    for index, entry in enumerate(data["courses"]):
        code = " ".join(str(entry.get("code", "")).split())
        title = " ".join(str(entry.get("title", "")).split())
        level = entry.get("level", "")
        if not code or not title or level not in LEVELS:
            raise ValueError(f"Catalog entry {index} is incomplete or has an unknown level: {entry!r}")
        if code in seen:
            continue
        seen.add(code)
        entries.append((code, title, level))
    return entries


def sync_courses(course_model, entries, *, retire_missing=False):
    """Make ``course_model`` rows match ``entries``.

    - A code not in the table is added, active.
    - A code already in the table gets the file's title and level. Its
      ``is_active`` flag is left alone, so a course retired by hand in the
      admin stays retired.
    - With ``retire_missing``, an active course absent from ``entries`` is
      retired. Nothing is ever deleted: sessions may reference it.

    Returns ``(added, updated, retired)`` counts.
    """
    existing = {course.code: course for course in course_model.objects.all()}

    to_add = []
    to_update = []
    for code, title, level in entries:
        course = existing.get(code)
        if course is None:
            to_add.append(course_model(code=code, title=title, level=level, is_active=True))
        elif course.title != title or course.level != level:
            course.title = title
            course.level = level
            to_update.append(course)

    course_model.objects.bulk_create(to_add)
    course_model.objects.bulk_update(to_update, ["title", "level"])

    retired = 0
    if retire_missing:
        wanted = {code for code, _, _ in entries}
        retired = (
            course_model.objects.filter(is_active=True)
            .exclude(code__in=wanted)
            .update(is_active=False)
        )

    return len(to_add), len(to_update), retired
