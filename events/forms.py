from django import forms
from django.conf import settings
from django.utils import timezone

from .models import CampusLocation, TutoringEvent


class TutoringEventForm(forms.ModelForm):
    """Create / edit form for a tutoring event pin.

    `host` is deliberately absent from Meta.fields: ownership is assigned from
    request.user in the view, never from submitted data. See AGENTS.md,
    "Restrict editable fields explicitly."
    """

    class Meta:
        model = TutoringEvent
        fields = [
            "title",
            "subject",
            "tutor",
            "date",
            "campus_location",
            "location",
            "latitude",
            "longitude",
            "isPublic",
        ]
        widgets = {
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "title": forms.TextInput(),
            "subject": forms.TextInput(),
            "tutor": forms.TextInput(),
            "location": forms.TextInput(),
            # Written by the map picker in campus_map.js.
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }
        labels = {
            "title": "Event title",
            "subject": "Course or subject",
            "tutor": "Tutor name shown to students",
            "date": "Starts at (Eastern Time)",
            "campus_location": "Building",
            "location": "Where exactly? (e.g. 2nd floor study room)",
            "isPublic": "Show this event publicly on the campus map",
        }
        help_texts = {
            "campus_location": "Optional. Pick a building, or drop the pin anywhere on campus.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Retired buildings stay in the table (campus_location is PROTECT) but
        # must not be offered for new events.
        self.fields["campus_location"].queryset = CampusLocation.objects.filter(
            is_active=True
        )
        self.fields["campus_location"].empty_label = "No specific building"
        self.fields["location"].required = False
        self.fields["isPublic"].required = False

    def clean_date(self):
        date = self.cleaned_data["date"]
        # An event in the past would save successfully and then never appear,
        # because the map query filters on date__gte=now().
        if date < timezone.now():
            raise forms.ValidationError("Pick a start time in the future.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if latitude is None or longitude is None:
            # Either the picker never ran or the inputs were stripped.
            if "latitude" not in self.errors and "longitude" not in self.errors:
                raise forms.ValidationError(
                    "Drop a pin on the map to set the event location."
                )
            return cleaned_data

        # The hidden inputs are attacker-controlled and the browser-side map
        # bounds prove nothing, so the campus bounding box is re-checked here.
        south, west, north, east = settings.SKILLSWAP_CAMPUS_BBOX
        if not (south <= float(latitude) <= north and west <= float(longitude) <= east):
            raise forms.ValidationError(
                "That location is outside the Florida Southern College campus."
            )

        return cleaned_data
