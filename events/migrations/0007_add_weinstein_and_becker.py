# Adds two buildings that were contributed to OpenStreetMap after
# 0006_seed_campus_locations ran.
#
# Source: OpenStreetMap, queried via Overpass on 2026-10-25 (data timestamp
# 2026-10-25T07:21:51Z) for way["building"]["name"] inside
# SKILLSWAP_CAMPUS_BBOX. Both ways were created at 2026-10-25T07:12:21Z.
# Coordinates are way centroids ("out center") and both were checked to fall
# inside SKILLSWAP_CAMPUS_BBOX -- roughly 261 m and 206 m inside its east edge.
#
# 0006 is already applied, so this is additive rather than an edit to it.

from django.db import migrations

BUILDINGS = [
    # (name, latitude, longitude, osm_way_id)
    ("Weinstein Computer Sciences Center", "28.030424", "-81.941962", 1571529972),
    ("Becker Business Building", "28.030081", "-81.941400", 1571529973),
]


def seed(apps, schema_editor):
    CampusLocation = apps.get_model("events", "CampusLocation")
    for name, latitude, longitude, _osm_way_id in BUILDINGS:
        CampusLocation.objects.update_or_create(
            name=name,
            defaults={"latitude": latitude, "longitude": longitude},
        )


def unseed(apps, schema_editor):
    """Remove these rows, but only where no event points at them.

    campus_location is PROTECT, so a building an event already references must
    survive this migration going backwards.
    """
    CampusLocation = apps.get_model("events", "CampusLocation")
    CampusLocation.objects.filter(
        name__in=[name for name, _lat, _lng, _osm in BUILDINGS],
        events__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_seed_campus_locations"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
