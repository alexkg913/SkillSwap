from django.db import models

# from events.models import Event

class DirectMessage(models.Model):
    sender = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self): 
        return f"From {self.sender} to {self.recipient} at {self.timestamp}"


