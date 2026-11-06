from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Profile


class SettingsHeaderAvatarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="student", email="student@example.com",
            first_name="Taylor", password="test-password"
        )
        self.client.force_login(self.user)

    def test_logout_form_precedes_profile_avatar_link(self):
        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertEqual(response.status_code, 200)
        logout_form = f'<form method="post" action="{reverse("logout")}">'
        avatar_link = (
            f'<a class="account-avatar" href="{reverse("user_profile:profile")}" '
            'aria-label="View your profile">'
        )
        self.assertContains(response, logout_form)
        self.assertContains(response, avatar_link)
        self.assertLess(response.content.index(logout_form.encode()), response.content.index(avatar_link.encode()))

    def test_uploaded_avatar_appears_in_header(self):
        Profile.objects.create(user=self.user, avatar="profiles/avatars/example.png")

        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertContains(response, 'class="account-avatar"')
        self.assertContains(response, 'src="/media/profiles/avatars/example.png" alt=""')

    def test_missing_avatar_uses_initial_in_header(self):
        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertContains(response, 'class="account-avatar"')
        self.assertContains(response, '<span aria-hidden="true">T</span>')


class ProfileHeaderAvatarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profile-student", email="profile-student@example.com",
            first_name="Taylor", password="test-password"
        )
        self.client.force_login(self.user)

    def test_logout_form_precedes_profile_avatar_link(self):
        response = self.client.get(reverse("user_profile:profile"))

        self.assertEqual(response.status_code, 200)
        logout_form = f'<form method="post" action="{reverse("logout")}">'
        avatar_link = (
            f'<a class="account-avatar" href="{reverse("user_profile:profile")}" '
            'aria-label="View your profile">'
        )
        self.assertContains(response, logout_form)
        self.assertContains(response, avatar_link)
        self.assertLess(response.content.index(logout_form.encode()), response.content.index(avatar_link.encode()))

    def test_uploaded_avatar_appears_in_header(self):
        Profile.objects.create(user=self.user, avatar="profiles/avatars/example.png")

        response = self.client.get(reverse("user_profile:profile"))

        self.assertContains(response, 'class="account-avatar"')
        self.assertContains(response, 'src="/media/profiles/avatars/example.png" alt=""')

    def test_missing_avatar_uses_initial_in_header(self):
        response = self.client.get(reverse("user_profile:profile"))

        self.assertContains(response, 'class="account-avatar"')
        self.assertContains(response, '<span aria-hidden="true">T</span>')
