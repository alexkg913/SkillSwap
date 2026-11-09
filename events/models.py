from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CampusLocation(models.Model):
    """A named campus building a tutoring event can be attached to.

    Seeded from a fixed list rather than resolved through a geocoder:
    Nominatim's usage policy forbids autocomplete-style querying, and a
    single-campus app does not need address search. See
    docs/campus-map-plan.md section 4.
    """

    name = models.CharField(max_length=120, unique=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90, latitude__lte=90),
                name="campuslocation_latitude_in_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180, longitude__lte=180),
                name="campuslocation_longitude_in_range",
            ),
        ]

    def __str__(self):
        return self.name


class TutoringEvent(models.Model):
    title = models.TextField()
    date = models.DateTimeField()
    location = models.TextField()
    subject = models.TextField()
    tutor = models.TextField()
    isPublic = models.BooleanField()

    # Map pin fields. `host` is the account that owns this event and is the
    # only basis for edit/cancel permission -- `tutor` above is display text
    # and cannot authorise anything.
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hosted_events",
    )

    # The event keeps its own coordinates even when a building is chosen, so
    # the map query stays single-table and relocating a building later does
    # not silently move past events. See docs/campus-map-plan.md section 5.
    campus_location = models.ForeignKey(
        CampusLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    # Cancelling hides an event from the map; it is never a row delete.
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latitude__gte=-90, latitude__lte=90),
                name="tutoringevent_latitude_in_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitude__gte=-180, longitude__lte=180),
                name="tutoringevent_longitude_in_range",
            ),
        ]
        indexes = [
            # The home map has one query: public, not cancelled, upcoming.
            models.Index(
                fields=["is_cancelled", "isPublic", "date"],
                name="event_map_query_idx",
            ),
        ]

    def __str__(self):
        return self.title


class TutorListing(models.Model):

    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    tutor = models.TextField()
    bio = models.TextField()
    subject = models.TextField()
    cost = models.FloatField()



class EventInteraction(models.Model):

    # limit status field to three options {default(no interaction), save event, going to event(RSVP)}
    class Status(models.TextChoices):
        DEFAULT = "default", "No Interaction" 
        GOING = "going" , "Going"
        SAVED = "saved" , "Saved"

    tutoring_event = models.ForeignKey(
        TutoringEvent, 
        on_delete=models.CASCADE)
    student = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length= 10,
        choices=Status.choices,
        default=Status.DEFAULT
    )
