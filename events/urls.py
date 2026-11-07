from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("new/", views.create_event, name="create"),
    path("<int:pk>/edit/", views.edit_event, name="edit"),
    path("<int:pk>/cancel/", views.cancel_event, name="cancel"),
    path("find-tutor/", views.find_tutor, name="find_tutor"),
    path("be-tutor/", views.be_tutor, name="be_tutor"),
    path("saved-events/", views.saved_events, name="saved_events")
]
