from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = "user_profile"

urlpatterns = [
    path("home_profile/", views.profile_page, name="profile"),

    path("home_profile/user_settings/", views.user_settings, name="user_settings"),
    path("home_profile/security_settings/", views.security_settings, name="security_settings"),

    # Use the same
    path("logout/", LogoutView.as_view(next_page="login"), name="logout"),

    # (These are for later, not main consideration)
    # path --> help_center
    # path --> contact_support
    # path --> skillswap_feedback

]
