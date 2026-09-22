import re
import uuid

from django import forms
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth.password_validation import validate_password

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

# Django built in Registration Forms for email and password authentication for the db
class RegistrationEmailForm(forms.Form):
    email = forms.EmailField()

class RegistrationPasswordForm(forms.Form):
    password = forms.CharField(
        strip=False,
        width=forms.PasswordInput,
    )

    # General security password validation checks according to the html visualizer
    def clean_password(self):
        password = self.cleaned_data["passord"]

        # Only validate password if it fits the security requirements
        if len(password) < 10:
            raise forms.ValidationError("Please use at least 10 characters!")

        if not re.search(r"[A-Z]", password):
            raise forms.ValidationError("Please include an uppercase letter!")

        if not re.search(r"[0-9]", password):
            raise forms.ValidationError("Please include at least a number!")

        if not re.search(r"[^A-Za-z0-9\s]", password):
            raise forms.ValidationError("Please include a special character!")

        return password

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
    email = request.session.get("registration_email")

    if not email:
        return redirect("user_register")

    form = RegistrationPasswordForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        username = f"user_{uuid.uuid4().hex}"
        password = form.cleaned_data["password"]

        # Pass the account to django password valid()
        candidate = User(username=username, email=email)

        try:
            validate_password(password, user=candidate)
        except ValidationError as errors:
            form.add_error("password", errors)

        # If it passes the initial password validation, accept the transaction unless there's an integrity error
        if not form.errors:
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
            except IntegrityError:
                form.add_error(
                    None,
                    "Unable to create this account oh no!"
                    "Try signing in or use another email :(("
                )
            else:
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                request.session.pop("registration_email", None)

                return redirect("user_profile:profile")

    return render(request, "login/user_register_password.html", {"form": form})


def forgot_pwd_page(request):
    return render(request, "login/forgot_pwd.html")
