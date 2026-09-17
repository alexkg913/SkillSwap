from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_page, name="login"),
    path("user_register/", views.register_page, name="user_register"),
    path("user_forgot_password/", views.forgot_pwd_page, name="user_forgot_pwd"),

]
