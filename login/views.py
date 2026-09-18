from django.shortcuts import render
from django.http import HttpResponse

def login_page(request):
    return render(request, "login/login_general.html")

def register_page(request):
    return render(request, "login/user_register.html")

def register_password(request):
    return render(request, "login/user_register_password.html")


def forgot_pwd_page(request):
    return render(request, "login/forgot_pwd.html")
