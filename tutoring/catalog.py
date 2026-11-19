"""Read-side helpers for the course catalog.

Courses live in the ``Course`` table (``tutoring.models.Course``), seeded from
``assets/fsc_courses.json`` and maintained in the Django admin. Nothing here is
cached in-process: an admin adding or retiring a course takes effect on the
next request, in every worker.

Only *active* courses are returned. A retired course stays in the table so
past sessions keep it, but it cannot be searched for, offered, or booked.

Course codes are the stored value and are treated as stable; titles are display
text only.
"""

from .models import Course

UNDERGRADUATE = Course.Level.UNDERGRADUATE
GRADUATE = Course.Level.GRADUATE
FOUNDATION_GROUP = Course.Level.FOUNDATION_GROUP


def active_courses(levels=()):
    """Active courses, optionally limited to ``levels``, ordered by code."""
    queryset = Course.objects.filter(is_active=True)
    if levels:
        queryset = queryset.filter(level__in=levels)
    return queryset


def courses():
    """Every active course as ``(code, title, level)`` triples, by code."""
    return tuple(active_courses().values_list("code", "title", "level"))


def course_titles():
    """Map every active course code to its title."""
    return dict(active_courses().values_list("code", "title"))


def is_valid_course(code):
    """True when ``code`` is an active course."""
    return bool(code) and active_courses().filter(code=code).exists()


def course_choices(*levels):
    """Django choices of ``(code, "CODE — Title")``, optionally by level.

    Called with no arguments every level is included. The value is the bare
    code so the stored data does not change when a title is reworded.
    """
    return tuple(
        (code, f"{code} — {title}")
        for code, title in active_courses(levels).values_list("code", "title")
    )


def _normalize(value):
    """Casefold and collapse whitespace for comparison."""
    return " ".join(value.split()).casefold()


def search_courses(query, levels=(), limit=20):
    """Bounded, case-insensitive course matches for a search box.

    Ranked deterministically: a course code prefix first, then a title prefix,
    then a code or title that merely contains the query, then (for
    multi-word queries) every word appearing somewhere. Matching is plain
    substring work -- no fuzzy spelling -- because course codes are short and
    structured, so a typo-tolerant match on them produces noise rather than
    help.

    The ranking runs in Python over the active rows for ``levels``: about a
    thousand short strings, which is cheaper than expressing the "MAT2022"
    space-insensitive match portably in SQL.
    """
    query = _normalize(query)[:80]
    if not query:
        return ()

    squashed_query = query.replace(" ", "")
    tokens = query.split()

    code_prefix, title_prefix, contained, all_tokens = [], [], [], []
    for code, title in active_courses(levels).values_list("code", "title"):
        code_key = _normalize(code)
        title_key = _normalize(title)
        if code_key.startswith(query) or code_key.replace(" ", "").startswith(squashed_query):
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
