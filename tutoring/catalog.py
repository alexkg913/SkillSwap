"""Read the bundled FSC course catalog without inlining it into a module.

The catalog data lives in ``assets/fsc_courses.json`` so it can be regenerated
from a new academic catalog without touching Python. See
``assets/fsc_courses.PROVENANCE.md`` for the source and how to refresh it.

Course codes are the stored value and are treated as stable; titles are display
text only.
"""

import json
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "assets" / "fsc_courses.json"

# Courses a student takes as part of the undergraduate programme. Graduate
# entries are kept separate because most peer tutoring happens at this level.
UNDERGRADUATE = "undergraduate"
GRADUATE = "graduate"

# A WRIGHT Foundations requirement met by any course in a group rather than by
# one numbered course, so it has no single catalog course number.
FOUNDATION_GROUP = "foundation_group"


@lru_cache(maxsize=1)
def courses():
    """Return the catalog as a tuple of ``(code, title, level)`` triples.

    File order is retained, which is subject prefix then course number, so a
    rendered dropdown is predictable. Duplicate codes are dropped, keeping the
    first entry, rather than silently shadowing one another in a dict.
    """
    with CATALOG_PATH.open(encoding="utf-8") as catalog:
        data = json.load(catalog)

    seen = set()
    entries = []
    for entry in data["courses"]:
        code = entry["code"].strip()
        if not code or code in seen:
            continue
        seen.add(code)
        entries.append((code, entry["title"].strip(), entry["level"]))
    return tuple(entries)


@lru_cache(maxsize=1)
def course_titles():
    """Map every known course code to its catalog title."""
    return {code: title for code, title, _ in courses()}


def is_valid_course(code):
    """True when ``code`` is a known course code.

    Server-side validation for anything that accepts a submitted course: a
    form field's own ``choices`` check only covers what that form rendered.
    """
    return code in course_titles()


@lru_cache(maxsize=None)
def course_choices(*levels):
    """Django choices of ``(code, "CODE — Title")``, optionally by level.

    Called with no arguments every level is included. The value is the bare
    code so the stored data does not change when a title is reworded.
    """
    wanted = set(levels)
    return tuple(
        (code, f"{code} — {title}")
        for code, title, level in courses()
        if not wanted or level in wanted
    )


def _normalize(value):
    """Casefold and collapse whitespace for comparison."""
    return " ".join(value.split()).casefold()


@lru_cache(maxsize=1)
def _search_index():
    """Precomputed comparison keys, built once per process.

    ``squashed`` has spaces removed so "mat2022" still finds "MAT 2022".
    """
    return tuple(
        (code, title, level, _normalize(code), _normalize(code).replace(" ", ""),
         _normalize(title))
        for code, title, level in courses()
    )


def search_courses(query, levels=(), limit=20):
    """Bounded, case-insensitive course matches for a search box.

    Ranked deterministically: a course code prefix first, then a title prefix,
    then a code or title that merely contains the query. Matching is plain
    substring work -- no fuzzy spelling -- because course codes are short and
    structured, so a typo-tolerant match on them produces noise rather than
    help.

    ``levels`` limits the result to those catalog levels; empty means all.
    """
    query = _normalize(query)[:80]
    if not query:
        return ()

    wanted = set(levels)
    squashed_query = query.replace(" ", "")
    tokens = query.split()

    code_prefix, title_prefix, contained, all_tokens = [], [], [], []
    for code, title, level, code_key, code_squashed, title_key in _search_index():
        if wanted and level not in wanted:
            continue
        if code_key.startswith(query) or code_squashed.startswith(squashed_query):
            code_prefix.append((code, title))
        elif title_key.startswith(query):
            title_prefix.append((code, title))
        elif query in code_key or query in title_key:
            contained.append((code, title))
        elif len(tokens) > 1 and all(
            token in code_key or token in title_key for token in tokens
        ):
            # "intro to soc" should find "SOC 1100 Introduction to Sociology"
            # even though it is not a literal substring of either field.
            all_tokens.append((code, title))

    results = code_prefix + title_prefix + contained + all_tokens
    return tuple(results[:limit])
