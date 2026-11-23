from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import TutoringEvent
from .models import DirectMessage, EventMessage

User = get_user_model()


class PageContentTests(TestCase):
    def setUp(self):
        self.ana = User.objects.create_user(username='ana', email='ana@example.com', password='pass12345!', first_name='Ana')
        self.ben = User.objects.create_user(username='ben', email='ben@example.com', password='pass12345!', first_name='Ben')
        DirectMessage.objects.create(sender=self.ben, recipient=self.ana, content='hello from ben')
        self.event = TutoringEvent.objects.create(
            title='Study session', date=timezone.now(), location='Library', subject='CS',
            tutor='Ana', isPublic=True, host=self.ana,
            latitude=Decimal('28.0'), longitude=Decimal('-81.0'),
        )
        EventMessage.objects.create(event=self.event, sender=self.ana, content='see you at the library')
        self.client.force_login(self.ana)

    def test_inbox_shows_first_name_not_email(self):
        response = self.client.get(reverse('inbox'))
        self.assertContains(response, 'Ben')
        self.assertNotContains(response, 'ben@example.com')

    def test_thread_shows_messages_and_no_email(self):
        response = self.client.get(reverse('thread', args=[self.ben.id]))
        self.assertContains(response, 'hello from ben')
        self.assertNotContains(response, 'ben@example.com')

    def test_event_chat_shows_messages_and_details(self):
        response = self.client.get(reverse('event_chat', args=[self.event.id]))
        self.assertContains(response, 'see you at the library')
        self.assertContains(response, 'Library')