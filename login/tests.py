from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="student", email="student@example.com", password="Test-pass-123!",
            first_name="Student Example", major="Computer Science",
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
        self.assertRedirects(response, reverse("user_profile:profile"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        profile = self.client.get(reverse("user_profile:profile"))
        self.assertTemplateUsed(profile, "user_profile/profile.html")
        self.assertContains(profile, "student@example.com")

    def test_signed_in_user_is_redirected_to_profile(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(self.url), reverse("user_profile:profile"))

    def test_incomplete_user_is_redirected_to_profile_setup_after_login(self):
        incomplete = get_user_model().objects.create_user(
            username="user_1234567890abcdef1234567890abcdef",
            email="incomplete@example.com",
            password="Test-pass-123!",
        )
        self.client.get(self.url)
        response = self.client.post(self.url, {
            "email": incomplete.email,
            "password": "Test-pass-123!",
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("user_profile_info"))

    def test_incomplete_authenticated_user_can_complete_profile_setup(self):
        incomplete = get_user_model().objects.create_user(
            username="user_abcdefabcdefabcdefabcdefabcdefab",
            email="incomplete@example.com",
            password="Test-pass-123!",
        )
        self.client.force_login(incomplete)
        setup_url = reverse("user_profile_info")
        self.client.get(setup_url)
        response = self.client.post(setup_url, {
            "username": "complete_student",
            "full_name": "Complete Student",
            "major": "Biology",
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, reverse("user_profile:profile"))
        incomplete.refresh_from_db()
        self.assertEqual(incomplete.username, "complete_student")
        self.assertEqual(incomplete.first_name, "Complete Student")
        self.assertEqual(incomplete.major, "Biology")

    def test_profile_requires_login(self):
        self.assertRedirects(
            self.client.get(reverse("user_profile:profile")),
            self.url + "?next=" + reverse("user_profile:profile"),
        )

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
        response = self.client.get(reverse("user_profile:profile"))
        self.assertContains(response, "Logout")
        response = self.client.post(reverse("logout"), {
            "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value,
        })
        self.assertRedirects(response, self.url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(self.client.get(self.url), 'name="email"')
        self.assertRedirects(self.submit(), reverse("user_profile:profile"))
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_logout_requires_post_and_csrf(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("logout")).status_code, 403)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))


class RegistrationProfileTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def _csrf(self, url):
        response = self.client.get(url)
        return self.client.cookies["csrftoken"].value

    def _start_registration(self):
        email_url = reverse("user_register")
        csrf = self._csrf(email_url)
        self.client.post(email_url, {
            "email": "new@example.com",
            "csrfmiddlewaretoken": csrf,
        })
        password_url = reverse("user_password")
        csrf = self._csrf(password_url)
        response = self.client.post(password_url, {
            "password": "Strong-pass-123!",
            "csrfmiddlewaretoken": csrf,
        })
        return response

    def test_password_step_creates_pending_account_and_redirects_to_profile_setup(self):
        response = self._start_registration()
        self.assertRedirects(response, reverse("user_profile_info"))
        user = get_user_model().objects.get(email="new@example.com")
        self.assertFalse(user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_setup_completes_pending_account(self):
        self._start_registration()
        setup_url = reverse("user_profile_info")
        csrf = self._csrf(setup_url)
        response = self.client.post(setup_url, {
            "username": "newstudent",
            "full_name": "New Student",
            "major": "Computer Science",
            "csrfmiddlewaretoken": csrf,
        })
        self.assertRedirects(response, reverse("user_profile:profile"))
        user = get_user_model().objects.get(email="new@example.com")
        self.assertTrue(user.is_active)
        self.assertEqual(user.username, "newstudent")
        self.assertEqual(user.first_name, "New Student")
        self.assertEqual(user.major, "Computer Science")

    def test_back_to_email_discards_pending_account(self):
        self._start_registration()
        response = self.client.get(reverse("user_register"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(email="new@example.com").exists())


class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = get_user_model().objects.create_user(
            username="resetstudent",
            email="reset@example.com",
            password="Old-pass-123!",
            is_active=True,
        )

    def _csrf(self, url):
        self.client.get(url)
        return self.client.cookies["csrftoken"].value

    def test_existing_email_redirects_to_password_reset(self):
        url = reverse("user_forgot_pwd")
        response = self.client.post(url, {
            "email": self.user.email,
            "csrfmiddlewaretoken": self._csrf(url),
        })
        self.assertRedirects(response, reverse("user_reset_password"))
        self.assertEqual(
            self.client.session["password_reset_user_id"],
            str(self.user.pk),
        )

    def test_unknown_email_does_not_redirect_or_set_reset_session(self):
        url = reverse("user_forgot_pwd")
        response = self.client.post(url, {
            "email": "missing@example.com",
            "csrfmiddlewaretoken": self._csrf(url),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "There is no active account")
        self.assertNotIn("password_reset_user_id", self.client.session)

    def test_reset_password_updates_password_and_returns_to_login(self):
        email_url = reverse("user_forgot_pwd")
        self.client.post(email_url, {
            "email": self.user.email,
            "csrfmiddlewaretoken": self._csrf(email_url),
        })

        reset_url = reverse("user_reset_password")
        response = self.client.post(reset_url, {
            "password": "New-pass-123!",
            "password_confirm": "New-pass-123!",
            "csrfmiddlewaretoken": self._csrf(reset_url),
        })

        self.assertRedirects(response, reverse("login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-pass-123!"))
        self.assertNotIn("password_reset_user_id", self.client.session)

    def test_reset_page_requires_verified_email_session(self):
        response = self.client.get(reverse("user_reset_password"))
        self.assertRedirects(response, reverse("user_forgot_pwd"))
