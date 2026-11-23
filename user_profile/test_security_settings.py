from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


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
