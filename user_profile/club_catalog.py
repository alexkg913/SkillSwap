"""Small, curated FSC club suggestions; not assertions of membership."""

from hashlib import sha256

from .skill_catalog import _close_spelling


MAJOR_CLUBS = (
    (("computer science", "data analytics", "interactive and game design"),
     ("FSCTV", "FSC Climbing Club", "Enactus", "The Southern", "Rotaract", "Cantilevers", "Beyond")),
    (("biology", "chemistry", "marine biology", "biotechnology", "nursing", "medical laboratory"),
     ("FSC Climbing Club", "Enactus", "Rotaract", "Fellowship of Christian Athletes", "Beyond", "ELEVATE", "Mocettes")),
    (("communication", "english", "film", "graphic design", "art history", "studio art"),
     ("The Southern", "FSCTV", "Cantilevers", "Enactus", "Fempowered", "Mocettes", "Rotaract")),
    (("finance", "accounting", "economics", "marketing", "sport business"),
     ("Enactus", "Rotaract", "The Southern", "FSCTV", "FSC Climbing Club", "ELEVATE", "Beyond")),
    (("music", "theatre", "dance", "education"),
     ("Mocettes", "Cantilevers", "FSCTV", "The Southern", "Rotaract", "Beyond", "ELEVATE")),
)


def club_names(choices):
    return tuple(name for name, _ in choices)


def suggested_clubs(major, username, choices, limit=6):
    """Choose stable, varied examples from the available club names."""
    names = club_names(choices)
    pool = names
    for prefixes, suggestions in MAJOR_CLUBS:
        if any(major.casefold().startswith(prefix) for prefix in prefixes):
            pool = tuple(name for name in suggestions if name in names)
            break
    pool = sorted(pool, key=lambda name: sha256(
        f"{username}:{major}:{name}".encode("utf-8")
    ).digest())
    return pool[:limit]


def search_clubs(query, choices, limit=12):
    """Rank short club queries by prefix, substring, then close spelling."""
    query = query.strip().casefold()[:80]
    if not query:
        return []
    names = club_names(choices)
    prefixes = [name for name in names if name.casefold().startswith(query)]
    contained = [name for name in names if query in name.casefold() and name not in prefixes]
    results = [*prefixes, *contained]
    if len(results) >= limit or len(query) < 3:
        return results[:limit]
    distance = 1 if len(query) < 5 else 2
    fuzzy = [name for name in names if name not in results and any(
        _close_spelling(query, word, distance)
        for word in name.casefold().replace(":", " ").split()
        if abs(len(word) - len(query)) <= distance
    )]
    return [*results, *fuzzy][:limit]
