from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_about_me_word_count(value):
    """Limit the About Me field to 300 words."""

    if len(value.split()) > 300:
        raise ValidationError("About Me cannot contain more than 300 words.")


class Profile(models.Model):
    """User-editable profile details that do not belong on the User model."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Avatar = Profile Picture in this instance :pp
    avatar = models.ImageField(
        upload_to="profiles/avatars/",
        blank=True,
    )
    banner_picture = models.ImageField(
        upload_to="profiles/banners/",
        blank=True,
    )

    about_me = models.TextField(
        blank=True,
        validators=[validate_about_me_word_count],
    )
    skills = models.JSONField(default=list, blank=True)
    classes_taken = models.JSONField(default=list, blank=True)
    interests_clubs = models.TextField(blank=True)

    # Stored as a baseline timezone abbreviation selected in the profile form.
    timezone = models.CharField(max_length=64, blank=True)

    # This is for students' country of origin btw, not where they currently reside since it would be the US duh
    country = models.CharField(max_length=100, blank=True)

    # Optional Field; City from students' country of origin
    city = models.CharField(max_length=100, blank=True)

    # ( -- FUTURE DEVELOPMENT - NOT REQUIRED FOR NOW -- )
    calling_code = models.CharField(max_length=8, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)

    # Social URLs for the users' boxes in the main profile
    github = models.URLField(blank=True)
    handshake = models.URLField(blank=True)
    yik_yak = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    discord = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    slack = models.URLField(blank=True)
    twitter = models.URLField(blank=True)

    def __str__(self):
        return f"Profile for {self.user.get_username()}"
