from django.contrib import admin
from .models import DirectMessage, EventMessage


# Register your models here.

admin.site.register(DirectMessage)
admin.site.register(EventMessage)