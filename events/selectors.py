"""Read-side queries for tutoring events.

Query logic lives here rather than in the views so views stay focused on
request handling. See docs/campus-map-plan.md section 6.
"""

from django.utils import timezone

from .models import CampusLocation, TutoringEvent


def upcoming_events_for_map():
    """Events eligible to appear as pins on the home map.

    One query, matched by the (is_cancelled, isPublic, date) index:
    public, not cancelled, not already over.
    """
    return (
        TutoringEvent.objects.filter(
            isPublic=True,
            is_cancelled=False,
            date__gte=timezone.now(),
        )
        .select_related("campus_location")
        .order_by("date")
    )


def _format_start(local_start):
    """Readable start time, e.g. "Nov 3, 2:30 PM ET".

    Built without strftime's %-d / %-I padding modifiers: those are a glibc
    extension and raise ValueError on Windows.
    """
    hour = local_start.hour % 12 or 12
    meridiem = "AM" if local_start.hour < 12 else "PM"
    return "%s %d, %d:%02d %s ET" % (
        local_start.strftime("%b"),
        local_start.day,
        hour,
        local_start.minute,
        meridiem,
    )


def serialize_event_for_map(event):
    """Public pin payload for one event.

    Exposes public fields only -- the home page is reachable without logging
    in. Nothing derived from the host *account* is included: `tutor` is the
    display text the host typed, while `host` is the FK used for permission
    checks and never leaves the server. No primary keys, no email addresses.

    Coordinates are cast to float on purpose. json_script serializes with
    DjangoJSONEncoder, which renders Decimal as a JSON *string*; campus_map.js
    validates coordinates with Number.isFinite(), so a string would fail that
    check and the map would fall back to its "unavailable" state.
    """
    local_start = timezone.localtime(event.date)
    return {
        "title": event.title,
        "subject": event.subject,
        "tutor": event.tutor,
        "building": event.campus_location.name if event.campus_location_id else "",
        # campus_map.js reads location_note for the popup's second line.
        "location_note": event.location,
        "starts_at": local_start.isoformat(),
        "starts_at_display": _format_start(local_start),
        "latitude": float(event.latitude),
        "longitude": float(event.longitude),
    }


def map_event_payload():
    """The full pin payload rendered into the home page."""
    return [serialize_event_for_map(event) for event in upcoming_events_for_map()]


def campus_building_coordinates():
    """Building coordinates for the form's picker, keyed by primary key.

    Keys are strings because that is what a <select> element's value is. Only
    active buildings are offered, matching TutoringEventForm's queryset.
    Floats, not Decimals, for the same json_script reason as above.
    """
    return {
        str(location.pk): {
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
        }
        for location in CampusLocation.objects.filter(is_active=True)
    }
