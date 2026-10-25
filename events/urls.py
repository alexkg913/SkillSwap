from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("new/", views.create_event, name="create"),
    path("<int:pk>/edit/", views.edit_event, name="edit"),
    path("<int:pk>/cancel/", views.cancel_event, name="cancel"),
]
