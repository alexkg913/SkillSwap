"""Read the bundled skill names without loading the catalog into a web page."""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "assets" / "linkedin_skills.txt"

# Editorial suggestions, not evidence that someone has these skills.
# First matching major prefix wins; a general set covers undeclared majors.
MAJOR_SUGGESTIONS = (
    (("computer science", "data analytics", "interactive and game design"),
     ("Programming", "Python", "Software Development", "Data Analysis", "Game Design", "Computer Science", "Artificial Intelligence")),
    (("biology", "biochemistry", "biotechnology", "chemistry", "interactive biology", "marine biology", "medical laboratory sciences"),
     ("Biology", "Biochemistry", "Chemistry", "Laboratory Skills", "Research", "Data Analysis", "Statistics")),
    (("mathematics", "applied mathematics"),
     ("Mathematics", "Statistics", "Data Analysis", "Research", "Programming", "Problem Solving")),
    (("accounting", "economics", "finance", "sport business", "marketing"),
     ("Accounting", "Finance", "Marketing", "Data Analysis", "Project Management", "Research")),
    (("graphic design", "studio art", "art history", "art education", "film"),
     ("Graphic Design", "Art", "Art History", "Animation", "Film Production", "Research")),
    (("music", "dance", "theatre"),
     ("Music", "Performing Arts", "Acting", "Public Speaking", "Theatre", "Education")),
    (("education", "elementary education", "secondary education"),
     ("Teaching", "Education", "Academic Tutoring", "Communication", "Leadership", "Research")),
    (("nursing",),
     ("Nursing", "Healthcare", "Biology", "Research", "Communication", "Critical Thinking")),
    (("communication", "political communication", "sports communication"),
     ("Communication", "Writing", "Public Speaking", "Social Media", "Marketing", "Research")),
    (("english", "history", "humanities", "philosophy", "religion", "social science", "political science", "phychology", "criminology", "spanish"),
     ("Writing", "Research", "Communication", "Critical Thinking", "Public Speaking", "Teaching")),
    (("environmental studies", "horticulture"),
     ("Environmental Science", "Horticulture", "Research", "Biology", "Data Analysis", "Project Management")),
)

GENERAL_SUGGESTIONS = (
    "Academic Tutoring", "Communication", "Research", "Writing",
    "Problem Solving", "Leadership", "Project Management",
)


@lru_cache(maxsize=1)
def skill_names():
    """Return unique nonempty names, retaining the first spelling and file order."""
    seen = set()
    names = []
    with CATALOG_PATH.open(encoding="utf-8") as catalog:
        for line in catalog:
            name = line.strip()
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                names.append(name)
    return tuple(names)


def suggested_skills(major, username, limit=6):
    """Return a stable, varied subset of relevant catalog entries for a major."""
    normalized_major = major.casefold().strip()
    pool = GENERAL_SUGGESTIONS
    for prefixes, suggestions in MAJOR_SUGGESTIONS:
        if any(normalized_major.startswith(prefix) for prefix in prefixes):
            pool = suggestions
            break

    available = {name.casefold(): name for name in skill_names()}
    candidates = [available[name.casefold()] for name in pool if name.casefold() in available]
    candidates.sort(key=lambda name: sha256(f"{username}:{major}:{name}".encode()).digest())
    return candidates[:limit]


@lru_cache(maxsize=1)
def skill_lookup():
    return {name.casefold(): name for name in skill_names()}


def _close_spelling(first, second, max_distance):
    if abs(len(first) - len(second)) > max_distance:
        return False
    previous = list(range(len(second) + 1))
    for i, character in enumerate(first, 1):
        current = [i]
        for j, other in enumerate(second, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (character != other),
            ))
        if min(current) > max_distance:
            return False
        previous = current
    return previous[-1] <= max_distance


def search_skills(query, limit=12):
    """Return bounded, case-insensitive matches, preferring prefixes to typos."""
    query = query.strip().casefold()[:80]
    if not query:
        return []

    names = skill_names()
    prefixes = [name for name in names if name.casefold().startswith(query)]
    if len(prefixes) >= limit:
        return sorted(prefixes, key=lambda name: (len(name), name.casefold()))[:limit]

    contained = [name for name in names if query in name.casefold() and name not in prefixes]
    results = sorted(prefixes, key=lambda name: (len(name), name.casefold()))
    results.extend(sorted(contained, key=lambda name: (len(name), name.casefold()))[:limit - len(results)])
    if len(results) >= limit or len(query) < 3:
        return results[:limit]

    distance = 1 if len(query) < 5 else 2
    fuzzy = [name for name in names if name not in results and any(
        _close_spelling(query, word, distance)
        for word in name.casefold().split()
        if abs(len(word) - len(query)) <= distance
    )]
    results.extend(sorted(fuzzy, key=lambda name: (len(name), name.casefold()))[:limit - len(results)])
    return results
