from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

User = get_user_model()

class MessageButtonTests(TestCase):
    def setUp(self):
        # Create two users for testing
        self.me = User.objects.create_user(username='me', email='me@example.com', password='pass12345!')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='pass54321!')

    def render_button(self, **context):
        return render_to_string('messaging/message_button.html', context).strip()

    def test_links_to_the_thread(self):
        html = self.render_button(person=self.other, user=self.me)
        self.assertIn(reverse('thread', args=[self.other.id]), html)

    def test_uses_a_custom_label(self):
        html = self.render_button(person=self.other, user=self.me, label='Message this tutor')
        self.assertIn('Message this tutor', html)

    def test_hidden_for_yourself(self):
        self.assertEqual(self.render_button(person=self.me, user=self.me), '')

    def test_hidden_when_logged_out(self):
        self.assertEqual(self.render_button(person=self.other, user=AnonymousUser()), '')

    def test_hidden_when_there_is_no_user(self):
        self.assertEqual(self.render_button(person='Some Tutor', user=self.me), '')