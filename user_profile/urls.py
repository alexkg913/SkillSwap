from django.urls import path, include
from django.contrib.auth.views import LogoutView
from . import views

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

app_name = "user_profile"

urlpatterns = [
    path("home_profile/", views.profile_page, name="profile"),

    path("home_profile/user_settings/", views.user_settings, name="user_settings"),
    path("home_profile/skill_options/", views.skill_options, name="skill_options"),
    path("home_profile/club_options/", views.club_options, name="club_options"),
    path("home_profile/security_settings/", views.security_settings, name="security_settings"),

    # Use the same
    path("logout/", LogoutView.as_view(next_page="home:index"), name="logout"),

    # (These are for later, not main consideration)
    # path --> help_center
    # path --> contact_support
    # path --> skillswap_feedback

]

# This is for development only for now -->
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
