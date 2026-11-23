from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import Profile
from .forms import FSC_CLUB_CHOICES
from .club_catalog import search_clubs, suggested_clubs
from .skill_catalog import suggested_skills, skill_names


class SettingsHeaderAvatarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="student", email="student@example.com",
            first_name="Taylor", password="test-password"
        )
        self.client.force_login(self.user)

    def test_sign_out_is_inside_dropdown(self):
        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertEqual(response.status_code, 200)
        logout_form = f'<form method="post" action="{reverse("logout")}">'
        trigger = '<summary class="account-menu__trigger"'
        self.assertContains(response, logout_form)
        self.assertContains(response, trigger)
        self.assertContains(response, '<button type="submit"><i class="fi fi-rr-sign-out-alt" aria-hidden="true"></i> Sign Out</button>')
        self.assertLess(response.content.index(trigger.encode()), response.content.index(logout_form.encode()))

    def test_uploaded_avatar_appears_in_header(self):
        Profile.objects.create(user=self.user, avatar="profiles/avatars/example.png")

        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertContains(response, 'class="account-menu__trigger"')
        self.assertContains(response, 'src="/media/profiles/avatars/example.png" alt=""')

    def test_missing_avatar_uses_initial_in_header(self):
        response = self.client.get(reverse("user_profile:user_settings"))

        self.assertContains(response, 'class="account-menu__trigger"')
        self.assertContains(response, '<span aria-hidden="true">T</span>')


class ProfileHeaderAvatarTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profile-student", email="profile-student@example.com",
            first_name="Taylor", password="test-password"
        )
        self.client.force_login(self.user)

    def test_sign_out_is_inside_dropdown(self):
        response = self.client.get(reverse("user_profile:profile"))

        self.assertEqual(response.status_code, 200)
        logout_form = f'<form method="post" action="{reverse("logout")}">'
        trigger = '<summary class="account-menu__trigger"'
        self.assertContains(response, logout_form)
        self.assertContains(response, trigger)
        self.assertContains(response, '<button type="submit"><i class="fi fi-rr-sign-out-alt" aria-hidden="true"></i> Sign Out</button>')
        self.assertLess(response.content.index(trigger.encode()), response.content.index(logout_form.encode()))

    def test_uploaded_avatar_appears_in_header(self):
        Profile.objects.create(user=self.user, avatar="profiles/avatars/example.png")

        response = self.client.get(reverse("user_profile:profile"))

        self.assertContains(response, 'class="account-menu__trigger"')
        self.assertContains(response, 'src="/media/profiles/avatars/example.png" alt=""')

    def test_missing_avatar_uses_initial_in_header(self):
        response = self.client.get(reverse("user_profile:profile"))

        self.assertContains(response, 'class="account-menu__trigger"')
        self.assertContains(response, '<span aria-hidden="true">T</span>')


class AccountMenuPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="menu-student", email="menu@example.com",
            first_name="Sam", last_name="Student", password="test-password"
        )

    def test_menu_on_app_pages_for_signed_in_user(self):
        self.client.force_login(self.user)
        for url in (
            reverse("home:index"),
            reverse("user_profile:profile"),
            reverse("user_profile:user_settings"),
            reverse("user_profile:security_settings"),
            reverse("events:create"),
            reverse("inbox"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'class="account-menu__trigger"')
                self.assertContains(response, "Sam Student")
                self.assertContains(response, "@menu-student")
                self.assertContains(response, 'data-appearance-select')
                self.assertContains(response, '<option value="light">Light</option>')
                self.assertContains(response, 'user_profile/css/appearance_light.css')
                self.assertContains(response, 'user_profile/js/appearance.js')
                self.assertContains(response, f'href="{reverse("user_profile:security_settings")}"')

    def test_anonymous_home_has_no_account_menu(self):
        response = self.client.get(reverse("home:index"))
        self.assertNotContains(response, 'class="account-menu__trigger"')


    def test_home_and_event_pages_load_dark_chrome_override(self):
        self.client.force_login(self.user)
        for url in (reverse("home:index"), reverse("events:create")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, 'home/css/appearance_dark.css')
                self.assertContains(response, 'data-appearance-select')

    def test_sign_out_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 302)
        self.assertFalse(self.client.session.get("_auth_user_id"))


class HeaderInboxLinkTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="inbox-student", password="test-password"
        )

    def test_signed_in_headers_link_to_inbox_before_avatar(self):
        self.client.force_login(self.user)
        for url in (
            reverse("home:index"),
            reverse("user_profile:profile"),
            reverse("user_profile:user_settings"),
            reverse("user_profile:security_settings"),
            reverse("events:create"),
            reverse("inbox"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(
                    response,
                    f'class="account-menu__inbox" href="{reverse("inbox")}" aria-label="Inbox"',
                )
                self.assertLess(
                    response.content.index(b'class="account-menu__inbox"'),
                    response.content.index(b'class="account-menu__trigger"'),
                )

    def test_anonymous_header_does_not_show_inbox_link(self):
        response = self.client.get(reverse("home:index"))
        self.assertNotContains(response, 'class="account-menu__inbox"')

    def test_inbox_link_destination_renders_inbox(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("inbox"))
        self.assertContains(response, "No conversations found.")


class InboxHeaderStyleTests(TestCase):
    def test_inbox_uses_profile_header_navigation(self):
        user = get_user_model().objects.create_user(
            username="header-student", password="test-password"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("inbox"))

        self.assertContains(response, 'css/main_profile.css')
        self.assertContains(response, '<header class="site-header">')
        self.assertContains(response, 'class="main-nav" aria-label="Main navigation"')
        self.assertContains(response, f'href="{reverse("user_profile:user_settings")}"')
        self.assertContains(response, 'class="account-menu__inbox"')


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


class ClubPickerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="club-student", email="clubs@example.com", password="test-password",
            major="Biology",
        )
        self.client.force_login(self.user)
        self.settings_url = reverse("user_profile:user_settings")

    def test_multiple_clubs_save_and_render_as_profile_tags(self):
        response = self.client.post(self.settings_url, {
            "major": "Biology",
            "interests_clubs": ["Beyond", "Greek Life: Theta Chi"],
        })

        self.assertRedirects(response, self.settings_url)
        self.assertEqual(Profile.objects.get(user=self.user).interests_clubs,
                         "Beyond\nGreek Life: Theta Chi")
        profile = self.client.get(reverse("user_profile:profile"))
        self.assertContains(profile, '<li class="profile-tag">Beyond</li>')
        self.assertContains(profile, '<li class="profile-tag">Greek Life: Theta Chi</li>')

    def test_existing_free_text_is_selected_and_can_be_retained(self):
        profile = Profile.objects.create(user=self.user, interests_clubs="Beyond, My Old Club")

        response = self.client.get(self.settings_url)

        self.assertEqual(response.context["form"]["interests_clubs"].value(),
                         ["Beyond", "My Old Club"])
        response = self.client.post(self.settings_url, {
            "major": "Biology", "interests_clubs": ["Beyond", "My Old Club"],
        })
        self.assertRedirects(response, self.settings_url)
        profile.refresh_from_db()
        self.assertEqual(profile.interests_clubs, "Beyond\nMy Old Club")

    def test_new_unlisted_club_is_rejected_without_changing_saved_clubs(self):
        profile = Profile.objects.create(user=self.user, interests_clubs="Beyond")

        response = self.client.post(self.settings_url, {
            "major": "Biology", "interests_clubs": ["Unlisted Club"],
        })

        self.assertFormError(response.context["form"], "interests_clubs",
                             "Select a valid choice. Unlisted Club is not one of the available choices.")
        profile.refresh_from_db()
        self.assertEqual(profile.interests_clubs, "Beyond")

    def test_settings_renders_only_selected_clubs_and_suggestions(self):
        response = self.client.get(self.settings_url)

        self.assertContains(response, 'id="club-search"')
        self.assertContains(response, 'user_profile/js/club_search.js')
        self.assertContains(response, 'value="Beyond"')
        self.assertLessEqual(response.content.count(b'name="interests_clubs"'), 6)


class ClubOptionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="club-search", email="club-search@example.com",
            password="test-password", major="Biology",
        )
        self.url = reverse("user_profile:club_options")

    def test_club_suggestions_are_bounded_and_major_specific(self):
        self.client.force_login(self.user)
        biology = self.client.get(self.url, {"major": "Biology"})
        computing = self.client.get(self.url, {"major": "Computer Science"})

        self.assertEqual(biology.status_code, 200)
        self.assertEqual(len(biology.json()["clubs"]), 6)
        self.assertNotEqual(set(biology.json()["clubs"]), set(computing.json()["clubs"]))
        self.assertTrue(set(biology.json()["clubs"]) <= set(dict(FSC_CLUB_CHOICES)))
        self.assertEqual(biology.json()["clubs"], suggested_clubs("Biology", self.user.username, FSC_CLUB_CHOICES))

    def test_typo_search_finds_club_and_no_match_returns_empty_list(self):
        self.client.force_login(self.user)

        self.assertIn("Rotaract", self.client.get(self.url, {
            "major": "Biology", "q": "rotarct",
        }).json()["clubs"])
        self.assertEqual(self.client.get(self.url, {
            "major": "Biology", "q": "zzzzzzz",
        }).json()["clubs"], [])
        self.assertIn("Beyond", search_clubs("beynd", FSC_CLUB_CHOICES))

    def test_anonymous_request_is_redirected(self):
        response = self.client.get(self.url, {"major": "Biology"})
        self.assertEqual(response.status_code, 302)

    def test_invalid_major_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"major": "unknown", "q": "Rotaract"})
        self.assertEqual(response.status_code, 400)


class SecurityPasswordChangeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="security-student",
            email="security@example.com",
            password="OriginalPass1!",
        )
        self.url = reverse("user_profile:security_settings")

    def test_anonymous_user_cannot_view_or_change_password(self):
        self.assertRedirects(self.client.get(self.url), f"{reverse('login')}?next={self.url}")
        self.assertRedirects(
            self.client.post(self.url, {
                "password": "ReplacementPass2!",
                "password_confirm": "ReplacementPass2!",
            }),
            f"{reverse('login')}?next={self.url}",
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))

    def test_get_shows_password_fields_without_current_password(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="password_confirm"')
        self.assertNotContains(response, 'name="current_password"')
        self.assertContains(response, 'type="submit"><i class="fi fi-rr-key" aria-hidden="true"></i> Change password</button>')

    def test_valid_change_updates_hash_and_keeps_user_signed_in(self):
        self.client.force_login(self.user)
        old_hash = self.user.password
        response = self.client.post(self.url, {
            "password": "ReplacementPass2!",
            "password_confirm": "ReplacementPass2!",
        }, follow=True)

        self.assertRedirects(response, self.url)
        self.assertContains(response, "Your password has been changed.")
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old_hash)
        self.assertFalse(self.user.check_password("OriginalPass1!"))
        self.assertTrue(self.user.check_password("ReplacementPass2!"))
        self.assertEqual(str(response.wsgi_request.user.pk), str(self.user.pk))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_mismatched_passwords_leave_old_password_intact(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "password": "ReplacementPass2!",
            "password_confirm": "DifferentPass3!",
        })
        self.assertContains(response, "The passwords do not match.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))

    def test_weak_password_leaves_old_password_intact(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "password": "short",
            "password_confirm": "short",
        })
        self.assertContains(response, "Please make your password at least 10 characters.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))

    def test_django_validator_rejects_password_similar_to_user(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {
            "password": "security@example.comA1!",
            "password_confirm": "security@example.comA1!",
        })
        self.assertContains(response, "too similar")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))

    def test_change_does_not_affect_another_account(self):
        other = get_user_model().objects.create_user(
            username="other-student",
            email="other@example.com",
            password="AnotherPass1!",
        )
        self.client.force_login(self.user)
        self.client.post(self.url, {
            "password": "ReplacementPass2!",
            "password_confirm": "ReplacementPass2!",
        })
        other.refresh_from_db()
        self.assertTrue(other.check_password("AnotherPass1!"))

    def test_post_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(self.url, {
            "password": "ReplacementPass2!",
            "password_confirm": "ReplacementPass2!",
        })
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))


class PasswordFeedbackPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="feedback-student",
            email="feedback@example.com",
            password="OriginalPass1!",
        )
        self.client.force_login(self.user)
        self.url = reverse("user_profile:security_settings")

    def test_password_fields_have_accessible_feedback(self):
        response = self.client.get(self.url)

        self.assertContains(response, "user_profile/js/password_feedback.js")
        self.assertContains(response, 'id="password-requirements"')
        self.assertContains(response, 'aria-describedby="password-rules"')
        for rule in ("rule-length", "rule-uppercase", "rule-special", "rule-number"):
            self.assertContains(response, f'id="{rule}"')
        self.assertContains(response, 'id="password-confirmation"')
        self.assertContains(response, 'id="password-match-status" role="status"')

    def test_invalid_confirmation_still_shows_server_error(self):
        response = self.client.post(self.url, {
            "password": "ReplacementPass2!",
            "password_confirm": "DifferentPass3!",
        })

        self.assertContains(response, "The passwords do not match.")
        self.assertContains(response, 'id="password-confirmation"')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OriginalPass1!"))
