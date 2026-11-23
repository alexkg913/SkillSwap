from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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
