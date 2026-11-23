from django import forms

from login.choices import FSC_MAJOR_CHOICES

from tutoring.catalog import course_choices
from .models import Profile
from .skill_catalog import skill_lookup, suggested_skills


TIMEZONE_CHOICES = [
    ("UTC", "UTC (UTC+0)"),
    ("EST", "EST (UTC-5)"),
    ("CST", "CST (UTC-6)"),
    ("MST", "MST (UTC-7)"),
    ("PST", "PST (UTC-8)"),
]

SKILL_CHOICES = [
    (skill, skill)
    for skill in [
        "Academic tutoring",
        "Active listening",
        "Communication",
        "Critical thinking",
        "Data analysis",
        "Graphic design",
        "Leadership",
        "Mathematics",
        "Microsoft Office",
        "Organization",
        "Peer mentoring",
        "Presentation",
        "Problem solving",
        "Programming",
        "Project management",
        "Research",
        "Social media",
        "Teamwork",
        "Time management",
        "Writing",
    ]
]

# Courses come from the tutoring.Course table rather than being inlined here.
# Passed as a callable so the database is queried on render, not at import.
COURSE_CHOICES = course_choices


class CatalogSkillsField(forms.MultipleChoiceField):
    def valid_value(self, value):
        return value.casefold() in skill_lookup() or value in dict(SKILL_CHOICES)


class ProfileForm(forms.ModelForm):
    """Form for the profile fields a user may edit themselves."""

    about_me = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Maximum 300 words.",
    )
    skills = CatalogSkillsField(
        choices=(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select all skills that apply.",
    )
    classes_taken = forms.MultipleChoiceField(
        choices=COURSE_CHOICES,
        required=False,
        label="Classes Taken",
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Select all completed courses that apply.",
    )
    classes_taken = forms.CharField(
        required=False,
        label="Classes Taken",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="List courses you have completed, one per line or separated by commas.",
    )
    interests_clubs = forms.CharField(
        required=False,
        label="Interests & Clubs",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="List your interests or clubs, one per line or separated by commas.",
    )
    timezone = forms.ChoiceField(
        choices=[("", "Select a timezone")] + TIMEZONE_CHOICES,
        required=False,
    )
    major = forms.ChoiceField(choices=FSC_MAJOR_CHOICES)

    class Meta:
        model = Profile
        fields = [
            "avatar",
            "banner_picture",
            "about_me",
            "skills",
            "classes_taken",
            "interests_clubs",
            "timezone",
            "country",
            "city",
            "calling_code",
            "phone_number",
            "github",
            "handshake",
            "yik_yak",
            "linkedin",
            "facebook",
            "discord",
            "instagram",
            "slack",
            "twitter",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            selected = self.data.getlist("skills")
            major = self.data.get("major", "")
        else:
            stored = self.instance.skills if self.instance.pk else []
            selected = stored if isinstance(stored, list) else [stored] if stored else []
            major = self.initial.get("major", "")

        names = dict.fromkeys([
            *selected,
            *suggested_skills(major, self.instance.user.username),
        ])
        self.fields["skills"].choices = [
            (name, name) for name in names if self.fields["skills"].valid_value(name)
        ]
