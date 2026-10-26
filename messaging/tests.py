from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import DirectMessage

User = get_user_model()


class MessagingTests(TestCase):
    def setUp(self):
        self.me = User.objects.create_user(username='me', email='me@example.com', password='pass12345!')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='pass12345!')
        self.third = User.objects.create_user(username='third', email='third@example.com', password='pass12345!')
        self.client.force_login(self.me)

    def test_inbox_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('inbox'))
        self.assertRedirects(response, '/login/?next=/messaging/inbox/', fetch_redirect_response=False)

    def test_thread_shows_only_this_conversation(self):
        DirectMessage.objects.create(sender=self.me, recipient=self.other, content='hi')
        DirectMessage.objects.create(sender=self.third, recipient=self.other, content='secret')
        response = self.client.get(reverse('thread', args=[self.other.id]))
        contents = [m.content for m in response.context['thread_messages']]
        self.assertEqual(contents, ['hi'])

    def test_reply_creates_message(self):
        response = self.client.post(reverse('thread', args=[self.other.id]), {'content': 'hello'})
        self.assertRedirects(response, reverse('thread', args=[self.other.id]))
        message = DirectMessage.objects.get()
        self.assertEqual(message.sender, self.me)
        self.assertEqual(message.recipient, self.other)

    def test_empty_reply_is_not_saved(self):
        self.client.post(reverse('thread', args=[self.other.id]), {'content': '   '})
        self.assertEqual(DirectMessage.objects.count(), 1)

    def test_cannot_message_yourself(self):
        response = self.client.post(reverse('thread', args=[self.me.id]), {'content': 'note to self'})
        self.assertRedirects(response, reverse('thread', args=[self.me.id]))
        self.assertEqual(DirectMessage.objects.count(), 0)