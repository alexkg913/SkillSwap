from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import EventInteraction, TutoringEvent
from .models import EventMessage

User = get_user_model()


class EventChatTests(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(username='host', email='host@example.com', password='pass12345!')
        self.going = User.objects.create_user(username='going', email='going@example.com', password='pass12345!')
        self.saved = User.objects.create_user(username='saved', email='saved@example.com', password='pass12345!')
        self.outsider = User.objects.create_user(username='outsider', email='outsider@example.com', password='pass12345!')
        self.event = TutoringEvent.objects.create(
            title='Study session', date=timezone.now(), location='Library', subject='CS',
            tutor='Host', isPublic=True, host=self.host,
            latitude=Decimal('28.0'), longitude=Decimal('-81.0'),
        )
        EventInteraction.objects.create(tutoring_event=self.event, student=self.going, status=EventInteraction.Status.GOING)
        EventInteraction.objects.create(tutoring_event=self.event, student=self.saved, status=EventInteraction.Status.SAVED)
        self.url = reverse('event_chat', args=[self.event.id])

    def test_host_can_open_and_post(self):
        self.client.force_login(self.host)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.post(self.url, {'content': 'hello'})
        self.assertEqual(EventMessage.objects.get().content, 'hello')

    def test_going_user_can_open(self):
        self.client.force_login(self.going)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_outsider_gets_403(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_outsider_cannot_post(self):
        self.client.force_login(self.outsider)
        self.client.post(self.url, {'content': 'sneaky'})
        self.assertEqual(EventMessage.objects.count(), 0)

    def test_saved_only_user_gets_403(self):
        self.client.force_login(self.saved)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_logged_out_goes_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/login/?next=' + self.url, fetch_redirect_response=False)