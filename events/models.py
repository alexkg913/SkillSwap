from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# Create your models here.
class TutoringEvent(models.Model):
    title = models.TextField()
    date = models.DateTimeField()
    location = models.TextField()
    subject = models.TextField()
    tutor = models.TextField()
    isPublic = models.BooleanField()
    


class TutorListing(models.Model):
    
    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    tutor = models.TextField()
    bio = models.TextField()
    subject = models.TextField()
    cost = models.FloatField()



class EventInteraction(models.Model):

    # limit status field to three options {default(no interaction), save event, going to event(RSVP)}
    class Status(models.TextChoices):
        DEFAULT = "default", "No Interaction" 
        GOING = "going" , "Going"
        SAVED = "saved" , "Saved"

    tutoring_event = models.ForeignKey(TutoringEvent, on_delete=models.CASCADE)
    student = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length= 10,
        choices=Status.choices,
        default=Status.DEFAULT
    )
    



