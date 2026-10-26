from django.conf import settings
from django.shortcuts import render

from events.selectors import map_event_payload, available_subjects, available_tutors


def map_config():
    """Server-provided Leaflet configuration for the campus map.

    Keeping these values in settings rather than in campus_map.js keeps
    deployment configuration out of static code and allows the tile provider to
    change without touching JavaScript.
    """
    return {
        "tile_url": settings.SKILLSWAP_MAP_TILE_URL,
        "tile_attribution": settings.SKILLSWAP_MAP_TILE_ATTRIBUTION,
        "tile_referrer_policy": settings.SKILLSWAP_MAP_TILE_REFERRER_POLICY,
        "center": list(settings.SKILLSWAP_MAP_CENTER),
        "default_zoom": settings.SKILLSWAP_MAP_DEFAULT_ZOOM,
    }


def map_events():
    """Public event pins for the campus map.

    Public fields only -- the home page is reachable without logging in. See
    events.selectors.serialize_event_for_map and
    docs/campus-map-plan.md section 6.
    """
    return map_event_payload()


def index(request):
    events = map_events()
    subjects = available_subjects()
    tutors = available_tutors()
    

    context = {
        "map_config": map_config(),
        "map_events": events,
        # The listings panel renders the same payload server-side, so the pins
        # are an enhancement rather than the only way to reach an event.
        "event_listings": events,
        "subjects": subjects,
        "tutors" : tutors,
        
    }
    return render(request, "home/index.html", context)
