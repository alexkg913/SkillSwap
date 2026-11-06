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


class ProfileSkillsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="skills-student", email="skills@example.com",
            password="test-password", major="Biology"
        )
        self.client.force_login(self.user)
        self.settings_url = reverse("user_profile:user_settings")

    def test_multiple_skills_are_saved_and_shown_as_profile_tags(self):
        response = self.client.post(self.settings_url, {
            "major": "Biology",
            "skills": ["Programming", "Writing"],
        })

        self.assertRedirects(response, self.settings_url)
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.skills, ["Programming", "Writing"])
        profile_response = self.client.get(reverse("user_profile:profile"))
        self.assertContains(profile_response, '<li class="profile-tag">Programming</li>')
        self.assertContains(profile_response, '<li class="profile-tag">Writing</li>')

    def test_saved_skills_are_checked_on_settings_page(self):
        Profile.objects.create(user=self.user, skills=["Mathematics", "Writing"])

        response = self.client.get(self.settings_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["skills"].value(), ["Mathematics", "Writing"])
        self.assertContains(response, 'type="checkbox"')

    def test_skill_search_is_labelled_and_checkbox_list_is_server_rendered(self):
        response = self.client.get(self.settings_url)

        self.assertContains(response, 'for="skill-search">Search skills</label>')
        self.assertContains(response, 'id="skill-search"')
        self.assertContains(response, 'user_profile/js/skill_search.js')
        self.assertContains(response, 'value="Programming"')
        self.assertContains(response, 'value="Writing"')

    def test_all_skills_can_be_revealed_without_submitting_form(self):
        response = self.client.get(self.settings_url)

        self.assertContains(response, 'id="skill-show-all" type="button"')
        self.assertContains(response, 'data-skill-seed="skills-student"')

    def test_unlisted_skill_is_rejected_without_changing_saved_skills(self):
        profile = Profile.objects.create(user=self.user, skills=["Writing"])

        response = self.client.post(self.settings_url, {
            "major": "Biology", "skills": ["Not a listed skill"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "skills", "Select a valid choice. Not a listed skill is not one of the available choices.")
        profile.refresh_from_db()
        self.assertEqual(profile.skills, ["Writing"])
