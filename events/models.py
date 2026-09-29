from django.db import models

# Create your models here.
class TutoringEvent(models.Model):
    title = models.TextField()
    date = models.DateTimeField()
    location = models.TextField()
    subject = models.TextField()
    tutor = models.TextField()
    isPublic = models.BooleanField()


class TutorListing(models.Model):
    listing_id = models.IntegerField
    tutor = models.TextField()
    bio = models.TextField()
    subject = models.TextField()
    cost = models.FloatField()


class EventInteraction(models.Model):
    student = models.TextField()



