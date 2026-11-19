from django.contrib import admin

from .models import TutorAvailability, TutorCourse, TutoringSession


@admin.register(TutorCourse)
class TutorCourseAdmin(admin.ModelAdmin):
    list_display = ["tutor", "course_code"]
    list_filter = ["course_code"]
    search_fields = ["course_code"]


@admin.register(TutorAvailability)
class TutorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["tutor", "start_at", "end_at"]


@admin.register(TutoringSession)
class TutoringSessionAdmin(admin.ModelAdmin):
    list_display = ["course_code", "tutor", "student", "start_at", "status"]
    list_filter = ["status", "course_code"]
