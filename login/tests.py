from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="student", email="student@example.com", password="Test-pass-123!"
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse("login")

    def submit(self, **overrides):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        data = {
            "email": self.user.email,
            "password": "Test-pass-123!",
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_regular_user_can_sign_in_with_email(self):
        response = self.submit()
        self.assertRedirects(response, self.url)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertContains(self.client.get(self.url), "Signed in as student@example.com")

    def test_missing_csrf_token_is_rejected(self):
        response = self.client.post(self.url, {
            "email": self.user.email, "password": "Test-pass-123!"
        })
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_incorrect_password_is_rejected(self):
        response = self.submit(password="wrong-password")
        self.assertContains(response, "Unable to sign in")
        self.assertNotContains(response, 'value="wrong-password"')
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_email_is_rejected(self):
        response = self.submit(email="unknown@example.com")
        self.assertContains(response, "Unable to sign in")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_user_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.submit()
        self.assertContains(response, "Unable to sign in")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_can_sign_out_and_log_in_as_regular_user(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="Admin-pass-123!"
        )
        self.client.force_login(admin)
        response = self.client.get(self.url)
        self.assertContains(response, "Sign out and use another account")
        response = self.client.post(reverse("logout"), {
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, self.url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(self.client.get(self.url), 'name="email"')
        self.assertRedirects(self.submit(), self.url)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_logout_requires_post_and_csrf(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 403)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
