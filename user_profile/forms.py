from django import forms

from .models import Profile


class ProfileForm(forms.ModelForm):
    """Form for the profile fields a user may edit themselves."""

    class Meta:
        model = Profile
        fields = [
            "avatar",
            "banner_picture",
            "about_me",
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
