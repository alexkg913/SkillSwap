# Seeds CampusLocation with Florida Southern College buildings.
#
# Source: OpenStreetMap, queried via Overpass on 2026-10-25 for
# way["building"]["name"] inside SKILLSWAP_CAMPUS_BBOX. Each entry below keeps
# its OSM way id so any coordinate can be re-checked at
# https://www.openstreetmap.org/way/<id>. Coordinates are the way centroids
# ("out center"), which is what a pin should point at.
#
# This is the subset of the 36 named buildings that a student could plausibly
# book a tutoring session in: academic buildings, the library, the archives,
# the technology centre and the multicultural centre. Deliberately excluded are
# residences, the two administration buildings, the President's Residence, the
# safety offices, Admissions, athletics facilities and the chapels.
#
# TODO(team): these are OSM's names, not FSC's official ones, and two were
# shortened for the picker dropdown -- see the comments inline. Someone with
# access to the official campus directory should confirm the spellings and add
# any study space this list misses. CampusLocation.is_active exists so a wrong
# entry can be retired without deleting rows that reference it.

from django.db import migrations

BUILDINGS = [
    # (name, latitude, longitude, osm_way_id)
    ("Allan Spivey Hall", "28.031001", "-81.946339", 128697683),
    ("Carlisle Rogers Building", "28.032603", "-81.948189", 128697666),
    ("Charles T. Thrift Building", "28.030482", "-81.944221", 128697667),
    # OSM: "Dr. Marcene H. and Robert E. Christoverson Humanities Building"
    ("Christoverson Humanities Building", "28.028880", "-81.950174", 224053019),
    # OSM: "Florida Southern College Wlliam F Chatlos Journalism Building"
    # (the OSM name misspells "William"; corrected here)
    ("Chatlos Journalism Building", "28.031836", "-81.950293", 1204184374),
    ("Edge Hall", "28.030294", "-81.946332", 128697670),
    ("Evett L. Simmons Multicultural Center", "28.030608", "-81.942030", 224438346),
    ("Herbert E. Wolfe Building", "28.030996", "-81.944464", 128697675),
    ("Jack M. Berry Citrus Building", "28.030596", "-81.945824", 128697677),
    ("Joseph-Reynolds Hall", "28.030996", "-81.946929", 128697678),
    ("L. A. Raulerson Building", "28.032077", "-81.948368", 227244582),
    ("Marjorie McKinley Music Building", "28.029844", "-81.949633", 224053021),
    ("Marshall and Vera Lea Rinker Technology Center", "28.031586", "-81.944566", 128697668),
    ("McKay Archives Center", "28.032602", "-81.949278", 224039785),
    ("Ordway Arts Building", "28.032634", "-81.946996", 128697679),
    ("Roux Library", "28.032497", "-81.948901", 128697682),
    ("Thad Buckner Building", "28.031358", "-81.949257", 224042304),
]


def seed(apps, schema_editor):
    CampusLocation = apps.get_model("events", "CampusLocation")
    for name, latitude, longitude, _osm_way_id in BUILDINGS:
        CampusLocation.objects.update_or_create(
            name=name,
            defaults={"latitude": latitude, "longitude": longitude},
        )


def unseed(apps, schema_editor):
    """Remove only the seeded rows, and only where nothing points at them.

    campus_location is PROTECT, so a seeded building an event already
    references must survive this migration going backwards.
    """
    CampusLocation = apps.get_model("events", "CampusLocation")
    CampusLocation.objects.filter(
        name__in=[name for name, _lat, _lng, _osm in BUILDINGS],
        events__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0005_campuslocation_event_pins"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
