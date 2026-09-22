from django import forms
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters


class RegistrationEmailForm(forms.Form):
    email = forms.EmailField()

@sensitive_post_parameters("password")
@never_cache
def login_page(request):
    if request.user.is_authenticated:
        return redirect("user_profile:profile")

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
            return redirect("user_profile:profile")

    return render(request, "login/login_general.html", {"form": form})

def register_page(request):
    form = RegistrationEmailForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        request.session["registration__email"] = form.cleaned_data["email"]
        return redirect("user_password")

    return render(request, "login/user_register.html", {"form": form})


def register_password(request):
    return render(request, "login/user_register_password.html")


def forgot_pwd_page(request):
    return render(request, "login/forgot_pwd.html")
