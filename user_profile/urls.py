from django.urls import path
from . import views

app_name = "user_profile"

urlpatterns = [
    path("", views.profile_page, name="profile"),

    # path --> user_settings
    # path --> security_settings
    # path --> home
    # path --> login.view/logout (in main pfp dropdown)

    # (These are for later, not main consideration)
    # path --> help_center
    # path --> contact_support
    # path --> skillswap_feedback

]
