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

    # Account role. One role at a time: a tutor offers courses and availability,
    # a student searches and books. Non-null with a false default so existing
    # and newly registered accounts are students until they opt in.
    is_tutor = models.BooleanField(
        default=False,
        verbose_name="is a tutor",
        help_text="Tutors list courses and availability; students book sessions.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
