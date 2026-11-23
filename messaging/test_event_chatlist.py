from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import EventInteraction, TutoringEvent

User = get_user_model()


class EventChatsListTests(TestCase):
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
        EventInteraction.objects.create(tutoring_event=self.event, student=self.going, going=True)
        EventInteraction.objects.create(tutoring_event=self.event, student=self.saved, saved=True)
        self.url = reverse('event_chats')

    def test_logged_out_goes_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, '/login/?next=' + self.url, fetch_redirect_response=False)

    def test_host_sees_their_event(self):
        self.client.force_login(self.host)
        response = self.client.get(self.url)
        self.assertContains(response, 'Study session')
        self.assertContains(response, reverse('event_chat', args=[self.event.id]))

    def test_going_user_sees_the_event(self):
        self.client.force_login(self.going)
        self.assertContains(self.client.get(self.url), 'Study session')

    def test_saved_only_user_does_not_see_it(self):
        self.client.force_login(self.saved)
        self.assertNotContains(self.client.get(self.url), 'Study session')

    def test_outsider_sees_the_empty_message(self):
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Study session')
        self.assertContains(response, 'no event chats yet')