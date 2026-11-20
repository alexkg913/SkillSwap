from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Profile
from .skill_catalog import suggested_skills, skill_names


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
        # Previous all-skills picker assertions, retained for reference:
        # self.assertContains(response, 'value="Programming"')
        # self.assertContains(response, 'value="Writing"')
        self.assertContains(response, 'data-search-url="%s"' % reverse("user_profile:skill_options"))
        self.assertContains(response, 'value="Biology"')

    def test_only_suggestions_render_without_show_all_button(self):
        response = self.client.get(self.settings_url)

        # Previous all-skills picker assertions, retained for reference:
        # self.assertContains(response, 'id="skill-show-all" type="button"')
        # self.assertContains(response, 'data-skill-seed="skills-student"')
        self.assertNotContains(response, 'id="skill-show-all" type="button"')
        self.assertLessEqual(response.content.count(b'name="skills"'), 6)

    def test_unlisted_skill_is_rejected_without_changing_saved_skills(self):
        profile = Profile.objects.create(user=self.user, skills=["Writing"])

        response = self.client.post(self.settings_url, {
            "major": "Biology", "skills": ["Not a listed skill"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "skills", "Select a valid choice. Not a listed skill is not one of the available choices.")
        profile.refresh_from_db()
        self.assertEqual(profile.skills, ["Writing"])


class SkillCatalogTests(TestCase):
    def test_catalog_names_are_unique_and_preserve_original_order(self):
        names = skill_names()

        self.assertEqual(len(names), len({name.casefold() for name in names}))
        self.assertIn("Programming", names)
        self.assertIn("Biology", names)

    def test_major_suggestions_are_relevant_catalog_entries(self):
        biology = suggested_skills("Biology", "student")
        computing = suggested_skills("Computer Science", "student")

        self.assertEqual(len(biology), 6)
        self.assertEqual(len(computing), 6)
        self.assertTrue(set(biology) <= set(skill_names()))
        self.assertTrue(set(computing) <= set(skill_names()))
        self.assertNotEqual(set(biology), set(computing))
        self.assertEqual(biology, suggested_skills("Biology", "student"))

    def test_undeclared_major_has_general_suggestions(self):
        suggestions = suggested_skills("Undeclared", "student")

        self.assertEqual(len(suggestions), 6)
        self.assertTrue(set(suggestions) <= set(skill_names()))


class SkillSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="search-student", email="search@example.com", password="test-password",
            major="Biology",
        )
        self.url = reverse("user_profile:skill_options")

    def test_anonymous_visitors_cannot_search_skills(self):
        response = self.client.get(self.url, {"major": "Biology", "q": "Python"})

        self.assertEqual(response.status_code, 302)

    def test_major_change_returns_different_bounded_suggestions(self):
        self.client.force_login(self.user)
        biology = self.client.get(self.url, {"major": "Biology"})
        computing = self.client.get(self.url, {"major": "Computer Science"})

        self.assertEqual(biology.status_code, 200)
        self.assertEqual(computing.status_code, 200)
        self.assertEqual(len(biology.json()["skills"]), 6)
        self.assertNotEqual(set(biology.json()["skills"]), set(computing.json()["skills"]))
        self.assertEqual(biology["Cache-Control"], "max-age=0, no-cache, no-store, must-revalidate, private")

    def test_search_matches_typo_without_rendering_whole_catalog(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"major": "Biology", "q": "programing"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Programming", response.json()["skills"])
        self.assertLessEqual(len(response.json()["skills"]), 12)

    def test_invalid_major_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"major": "unlisted", "q": "Python"})

        self.assertEqual(response.status_code, 400)

    def test_catalog_skill_not_in_suggestions_can_be_saved(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("user_profile:user_settings"), {
            "major": "Biology", "skills": ["Python"],
        })

        self.assertRedirects(response, reverse("user_profile:user_settings"))
        self.assertEqual(Profile.objects.get(user=self.user).skills, ["Python"])
