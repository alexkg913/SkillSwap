from django.contrib import admin, messages

from .models import Course, TutorAvailability, TutorCourse, TutoringSession


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Add, retire, and restore courses.

    Retiring (``is_active`` off) is the normal way to remove a course: it
    disappears from search, offers, and booking, but past sessions keep it.
    Deleting works only while no session references the course.
    """

    list_display = ["code", "title", "level", "is_active"]
    list_filter = ["is_active", "level"]
    search_fields = ["code", "title"]
    list_editable = ["is_active"]
    ordering = ["code"]
    actions = ["retire_courses", "restore_courses"]

    def get_readonly_fields(self, request, obj=None):
        # Offers and sessions store the code, so it is the course's identity.
        # Changing it would silently rename history; add a new course instead.
        if obj is not None:
            return ["code"]
        return []

    @admin.action(description="Retire selected courses")
    def retire_courses(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Retired {count} course(s).", messages.SUCCESS)

    @admin.action(description="Restore selected courses")
    def restore_courses(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Restored {count} course(s).", messages.SUCCESS)


@admin.register(TutorCourse)
class TutorCourseAdmin(admin.ModelAdmin):
    list_display = ["tutor", "course"]
    list_select_related = ["tutor", "course"]
    search_fields = ["course__code", "course__title"]
    autocomplete_fields = ["course"]


@admin.register(TutorAvailability)
class TutorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["tutor", "start_at", "end_at"]


@admin.register(TutoringSession)
class TutoringSessionAdmin(admin.ModelAdmin):
    list_display = ["course", "tutor", "student", "start_at", "status"]
    list_select_related = ["course", "tutor", "student"]
    list_filter = ["status"]
    search_fields = ["course__code"]
    autocomplete_fields = ["course"]
