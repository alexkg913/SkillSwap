"""Load a catalog JSON file into the Course table.

    python manage.py sync_courses                      # assets/fsc_courses.json
    python manage.py sync_courses path/to/catalog.json
    python manage.py sync_courses --retire-missing     # also retire dropped courses

Adds new codes and refreshes titles and levels. Never deletes, and never
re-activates a course retired in the admin. Run it after regenerating the JSON
for a new academic year; see assets/fsc_courses.PROVENANCE.md.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tutoring.course_import import CATALOG_PATH, read_catalog_file, sync_courses
from tutoring.models import Course


class Command(BaseCommand):
    help = "Add and update courses from a catalog JSON file."

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(CATALOG_PATH))
        parser.add_argument(
            "--retire-missing",
            action="store_true",
            help="Retire active courses that the file no longer lists.",
        )

    def handle(self, *args, path, retire_missing, **options):
        try:
            entries = read_catalog_file(path)
        except (OSError, ValueError, KeyError) as error:
            raise CommandError(f"Could not read {path}: {error}") from error

        with transaction.atomic():
            added, updated, retired = sync_courses(
                Course, entries, retire_missing=retire_missing
            )

        self.stdout.write(self.style.SUCCESS(
            f"{len(entries)} courses in file: {added} added, {updated} updated, "
            f"{retired} retired."
        ))
