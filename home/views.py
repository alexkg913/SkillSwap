from django.conf import settings
from django.shortcuts import render

from events.models import EventInteraction
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


def map_events(query="", subject="", tutor=""):
    """Public event pins for the campus map.

    Public fields only -- the home page is reachable without logging in. See
    events.selectors.serialize_event_for_map and
    docs/campus-map-plan.md section 6.
    """
    return map_event_payload(
        query=query,
        subject=subject,
        tutor=tutor,
    )


def index(request):
    query = request.GET.get("q", "").strip()
    subject = request.GET.get("subject", "")
    tutor = request.GET.get("tutor", "")

    events = map_events(
        query=query,
        subject=subject,
        tutor=tutor,

    )
    interactions = {}
    if request.user.is_authenticated:
        interactions = {
            interaction.tutoring_event_id: interaction
            for interaction in EventInteraction.objects.filter(
                student=request.user,
                tutoring_event_id__in=[event["id"] for event in events],
            )
        }

    event_listings = []
    for event in events:
        interaction = interactions.get(event["id"])
        event_listings.append({
            **event,
            "is_saved": interaction.saved if interaction else False,
            "is_going": interaction.going if interaction else False,
        })

    subjects = available_subjects()
    tutors = available_tutors()
    

    context = {
        "map_config": map_config(),
        # Action IDs and student-specific state belong only in the listings,
        # not in the public map JSON.
        "map_events": [
            {key: value for key, value in event.items() if key != "id"}
            for event in events
        ],
        "event_listings": event_listings,
        "subjects": subjects,
        "tutors" : tutors,
        "query": query,
        
    }
    return render(request, "home/index.html", context)

