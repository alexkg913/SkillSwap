"""Move the course catalog from assets/fsc_courses.json into a Course table.

Existing ``course_code`` values are preserved: the new foreign keys point at
``Course.code`` (``to_field="code"``), so the stored text does not change, only
gains a constraint. Order matters:

1. create ``Course`` and seed it from the JSON file;
2. add an inactive placeholder for any stored code the file no longer lists,
   so no existing offer or booking is orphaned by the new constraint;
3. drop the constraint and index that name ``course_code``;
4. turn ``course_code`` into a foreign key, then rename it to ``course``;
5. recreate the constraint and index on ``course``.
"""

import django.db.models.deletion
from django.db import migrations, models

from tutoring.course_import import read_catalog_file, sync_courses


def seed_courses(apps, schema_editor):
    Course = apps.get_model("tutoring", "Course")
    TutorCourse = apps.get_model("tutoring", "TutorCourse")
    TutoringSession = apps.get_model("tutoring", "TutoringSession")

    sync_courses(Course, read_catalog_file())

    known = set(Course.objects.values_list("code", flat=True))
    stored = set(TutorCourse.objects.values_list("course_code", flat=True))
    stored |= set(TutoringSession.objects.values_list("course_code", flat=True))
    Course.objects.bulk_create([
        Course(code=code, title=code, level="undergraduate", is_active=False)
        for code in sorted(stored - known)
    ])


def unseed_courses(apps, schema_editor):
    # Reversing drops the table anyway; nothing to undo row by row.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tutoring", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=32, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("level", models.CharField(choices=[("undergraduate", "Undergraduate"), ("graduate", "Graduate"), ("foundation_group", "Foundations group")], default="undergraduate", max_length=20)),
                ("is_active", models.BooleanField(default=True, help_text="Untick to retire the course: it stops appearing in search and cannot be offered or booked, but past sessions keep it.")),
            ],
            options={
                "ordering": ["code"],
            },
        ),
        migrations.RunPython(seed_courses, unseed_courses),
        migrations.RemoveConstraint(
            model_name="tutorcourse",
            name="tutorcourse_unique_per_tutor",
        ),
        migrations.RemoveIndex(
            model_name="tutorcourse",
            name="tutorcourse_search_idx",
        ),
        migrations.AlterField(
            model_name="tutorcourse",
            name="course_code",
            field=models.ForeignKey(db_column="course_code", on_delete=django.db.models.deletion.CASCADE, related_name="tutor_offers", to="tutoring.course", to_field="code"),
        ),
        migrations.RenameField(
            model_name="tutorcourse",
            old_name="course_code",
            new_name="course",
        ),
        migrations.AlterField(
            model_name="tutorcourse",
            name="course",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tutor_offers", to="tutoring.course", to_field="code"),
        ),
        migrations.AlterField(
            model_name="tutoringsession",
            name="course_code",
            field=models.ForeignKey(db_column="course_code", on_delete=django.db.models.deletion.PROTECT, related_name="sessions", to="tutoring.course", to_field="code"),
        ),
        migrations.RenameField(
            model_name="tutoringsession",
            old_name="course_code",
            new_name="course",
        ),
        migrations.AlterField(
            model_name="tutoringsession",
            name="course",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sessions", to="tutoring.course", to_field="code"),
        ),
        migrations.AlterModelOptions(
            name="tutorcourse",
            options={"ordering": ["course"]},
        ),
        migrations.AddConstraint(
            model_name="tutorcourse",
            constraint=models.UniqueConstraint(fields=("tutor", "course"), name="tutorcourse_unique_per_tutor"),
        ),
        migrations.AddIndex(
            model_name="tutorcourse",
            index=models.Index(fields=["course", "tutor"], name="tutorcourse_search_idx"),
        ),
    ]
