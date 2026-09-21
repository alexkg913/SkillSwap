import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    # Generate unique id to reference each account, Django pre hashes passwords by default
    # Major is a custom text field
    id = models.UUIDField(
        primary_key = True,
        default=uuid.uuid4,
        editable=False,
    )

    email = models.EmailField(unique=True)
    major = models.CharField(max_length=100, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
