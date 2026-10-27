from django.conf import settings
from django.db import models


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

    about_me = models.TextField(blank=True)

    # Will be updated with the feature/timezones branch
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
