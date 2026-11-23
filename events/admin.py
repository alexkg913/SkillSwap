from django.contrib import admin

from .models import CampusLocation, EventInteraction, TutoringEvent, TutorListing


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "latitude", "longitude", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(TutoringEvent)
class TutoringEventAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "date", "campus_location", "isPublic", "is_cancelled")
    list_filter = ("isPublic", "is_cancelled", "campus_location")
    search_fields = ("title", "subject", "tutor")
    list_select_related = ("campus_location",)
    autocomplete_fields = ("campus_location",)


admin.site.register(TutorListing)
admin.site.register(EventInteraction)
