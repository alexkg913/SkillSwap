# Adds the buildings that appeared in OpenStreetMap on 2026-10-25, and retires
# the ones the team decided should not be offered as tutoring venues.
#
# Source: OpenStreetMap, queried via Overpass on 2026-10-25 (data timestamp
# 2026-10-25T07:26:56Z) for way["building"]["name"] inside
# SKILLSWAP_CAMPUS_BBOX. Each entry keeps its OSM way id so any coordinate can
# be re-checked at https://www.openstreetmap.org/way/<id>. Coordinates are way
# centroids ("out center").
#
# Everything added here is seeded is_active=False, so the rows exist for
# reference and for any future event that needs them, but none are offered in
# the picker dropdown:
#
#   - Student Housing (Dell, Hollis, Jenkins) and the Admissions Center were
#     excluded by name.
#   - The three Publix Commons are not tagged "Student Housing" in OSM, but the
#     #61/#62/#63 unit numbering reads as residential, so they are treated the
#     same way. Flip is_active to offer them.
#
# Also retires two buildings that 0006 seeded as active: Allan Spivey Hall and
# Joseph-Reynolds Hall.
#
# Deactivating rather than deleting: campus_location is PROTECT, so a delete
# would refuse on any building an event already references, and is_active=False
# already removes it from the dropdown (see TutoringEventForm.__init__). It is
# also reversible, which a delete is not.
#
# Nicholas Residence Hall and Wesley Residence Hall are intentionally absent
# from CampusLocation entirely -- 0006 never seeded residences -- so they are
# already unavailable and need no row here.

from django.db import migrations

# (name, latitude, longitude, osm_way_id)
ADD_INACTIVE = [
    ("FSC Publix Commons #61", "28.032948", "-81.944412", 1571529977),
    ("FSC Publix Commons #62", "28.032494", "-81.944410", 1571529978),
    ("FSC Publix Commons #63", "28.032491", "-81.943747", 1571529979),
    ("Florida Southern College Admissions Center", "28.030259", "-81.942690", 1571529974),
    ("Florida Southern College Student Housing Dell Hall", "28.031641", "-81.943637", 1571529976),
    ("Florida Southern College Student Housing Hollis Hall", "28.031995", "-81.943690", 1571529975),
    ("Florida Southern College Student Housing Jenkins Hall", "28.032708", "-81.943295", 1571529980),
]

DEACTIVATE = [
    "Allan Spivey Hall",
    "Joseph-Reynolds Hall",
]


def curate(apps, schema_editor):
    CampusLocation = apps.get_model("events", "CampusLocation")

    for name, latitude, longitude, _osm_way_id in ADD_INACTIVE:
        CampusLocation.objects.update_or_create(
            name=name,
            defaults={
                "latitude": latitude,
                "longitude": longitude,
                "is_active": False,
            },
        )

    CampusLocation.objects.filter(name__in=DEACTIVATE).update(is_active=False)


def uncurate(apps, schema_editor):
    """Reverse: re-offer the two retired buildings, drop the added rows.

    Added rows are removed only where no event references them, since
    campus_location is PROTECT.
    """
    CampusLocation = apps.get_model("events", "CampusLocation")

    CampusLocation.objects.filter(name__in=DEACTIVATE).update(is_active=True)

    CampusLocation.objects.filter(
        name__in=[name for name, _lat, _lng, _osm in ADD_INACTIVE],
        events__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0007_add_weinstein_and_becker"),
    ]

    operations = [
        migrations.RunPython(curate, uncurate),
    ]
