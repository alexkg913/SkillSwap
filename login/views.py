from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

@sensitive_post_parameters("password")
@never_cache
def login_page(request):
    form = AuthenticationForm(request)
    if request.method == "POST":
        # AuthenticationForm calls the login identifier "username", even
        # when our User.USERNAME_FIELD is email.
        form = AuthenticationForm(request, data={
            "username": request.POST.get("email", ""),
            "password": request.POST.get("password", ""),
        })
        if form.is_valid():
            login(request, form.get_user())
            return redirect("login")

    return render(request, "login/login_general.html", {"form": form})

def register_page(request):
    return render(request, "login/user_register.html")

def register_password(request):
    return render(request, "login/user_register_password.html")


def forgot_pwd_page(request):
    return render(request, "login/forgot_pwd.html")
