from django.db import models

# from django.conf import settings

# class Profile(models.Model):
#     """Non-authentication details associated with one account."""

#     user = models.OneToOneField(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="profile",
#     )

#     profile_picture = models.ImageField(
#         upload_to="profiles/", blank=True
#     )

#     banner_picture = models.ImageField(
#         upload_to="profile_banners/", blank=True
#     )

#     bio/tagline = models.TextField(blank=True)
#     about_me = models.TextField(blank=True)
#     timezone = models.CharField(max_length=64, blank=True)
#     country = models.CharField(max_length=100, blank=True)
#     city = models.CharField(max_length=100, blank=True)
#
# Skills, classes, clubs, and social accounts are usually better as
# separate related models when users can have multiple entries or when
# those values need to be searched/filtered. Keep email and password on
# the User model; access email through profile.user.email and never copy
# or expose the password here. (opencode written after planning)
