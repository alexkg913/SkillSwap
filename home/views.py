from django.conf import settings
from django.shortcuts import render


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

    The events app that owns TutoringEvent is not part of this branch, so there
    is nothing to pin yet and the map renders empty. When it lands, this returns
    the payload from events.selectors and must expose public fields only -- no
    account emails, no user IDs. See docs/campus-map-plan.md section 6.
    """
    return []


def index(request):
    context = {
        "map_config": map_config(),
        "map_events": map_events(),
    }
    return render(request, "home/index.html", context)
