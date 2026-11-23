from django.urls import path

from . import views

app_name = "tutoring"

urlpatterns = [
    # Shared
    path("courses/", views.course_options, name="course_options"),
    # Student
    path("find/", views.find_tutor, name="find"),
    path("book/", views.book_session, name="book"),
    path("sessions/", views.my_sessions, name="sessions"),
    path("sessions/<int:pk>/cancel/", views.cancel_session, name="cancel"),
    # Tutor
    path("setup/", views.tutor_courses, name="setup"),
    path("availability/", views.tutor_availability, name="availability"),
    path("availability/<int:pk>/delete/", views.delete_availability,
         name="delete_availability"),
]
