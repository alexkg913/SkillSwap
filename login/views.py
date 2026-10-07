import re
import uuid

from django import forms
from django.contrib.auth import login, get_user_model
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
        widget=forms.PasswordInput,
    )

    # General security password validation checks according to the html visualizer
    def clean_password(self):
        password = self.cleaned_data["password"]

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


FSC_MAJOR_CHOICES = tuple(
    (major, major) for major in (
        "Accounting",
        "Applied Mathematics and Statistics",
        "Art Education",
        "Art History and Museum Studies",
        "Biochemistry and Molecular Biology",
        "Biology",
        "Biotechnology",
        "Chemistry",
        "Communication",
        "Communication: Advertising and Public Relations",
        "Communication: Interpersonal and Organizational Communication",
        "Communication: Media Strategies and Production",
        "Communication: Multimedia Journalism",
        "Computer Science",
        "Computer Science: Artificial Intelligence and Machine Learning",
        "Computer Science: Cybersecurity",
        "Computer Science: Full-Stack Web Development",
        "Criminology",
        "Dance Performance and Choreography",
        "Data Analytics",
        "Economics",
        "Elementary Education",
        "English",
        "Environmental Studies",
        "Exercise Science",
        "Film",
        "Finance",
        "Graphic Design",
        "History",
        "Horticulture, Land, and Resource Management",
        "Humanities",
        "Integrative Biology",
        "Interactive and Game Design",
        "Marine Biology",
        "Marketing",
        "Mathematics",
        "Medical Laboratory Sciences",
        "Music",
        "Music Education",
        "Music: Music Business",
        "Music Performance",
        "Nursing",
        "Philosophy",
        "Political Communication",
        "Political Science",
        "Psychology",
        "Religion",
        "Secondary Education",
        "Social Sciences",
        "Spanish",
        "Sport Business Management",
        "Sports Communication and Marketing",
        "Studio Art",
        "Theatre Arts",
        "Theatre Arts: Musical Theatre",
        "Theatre Arts: Technical Theatre and Design",
        "Theatre Arts: Theatre Performance",
        "Undeclared",
    )
)


class RegistrationProfileForm(forms.Form):
    username = forms.CharField(max_length=150)
    full_name = forms.CharField(max_length=150)
    major = forms.ChoiceField(choices=FSC_MAJOR_CHOICES)

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput,
    )

    password_confirm = forms.CharField(
        strip=False,
        widget=forms.PasswordInput,
    )

    def clean_password(self):
        password = self.cleaned_data["password"]

        # Standard Checks of password integrity
        if len(password) < 10:
            raise forms.ValidationError(
                "Please make your password at least 10 characters."
            )

        if not re.search(r"[A-Z]", password):
            raise forms.ValidationError(
                "Please include an uppercase letter."
            )

        if not re.search(r"[0-9]", password):
            raise forms.ValidationError(
                "Please include at least a number."
            )

        if not re.search(r"[^A-Za-z0-9\s]", password):
            raise forms.ValidationError(
                "Please include a special character."
            )


        return password

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error(
                "password_confirm",
                "The passwords do not match.",
            )

        return cleaned_data

def profile_setup_required(user):
    generated_username = re.fullmatch(r"user_[0-9a-f]{32}", user.username or "")
    return bool(
        not user.first_name.strip()
        or not user.major.strip()
        or generated_username
    )


def _discard_pending_registration(request):
    pending_id = request.session.pop("pending_registration_user_id", None)
    if pending_id:
        User = get_user_model()
        User.objects.filter(pk=pending_id, is_active=False).delete()

@sensitive_post_parameters("password")
@never_cache
def login_page(request):
    if request.user.is_authenticated:
        if profile_setup_required(request.user):
            return redirect("user_profile_info")
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
            user = form.get_user()
            login(request, user)
            if profile_setup_required(user):
                return redirect("user_profile_info")
            return redirect("user_profile:profile")

    return render(request, "login/login_general.html", {"form": form})

def register_page(request):
    _discard_pending_registration(request)
    form = RegistrationEmailForm(
        request.POST if request.method == "POST" else None
    )

    if request.method == "POST" and form.is_valid():
        request.session["registration_email"] = form.cleaned_data["email"]
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
                        password=password,
                        is_active=False,
                    )
            except IntegrityError:
                form.add_error(
                    None,
                    "Unable to create this account oh no!"
                    "Try signing in or use another email :(("
                )
            else:
                request.session["pending_registration_user_id"] = str(user.pk)
                return redirect("user_profile_info")

    return render(request, "login/user_register_password.html", {"form": form})


def register_profile(request):
    pending_id = request.session.get("pending_registration_user_id")
    User = get_user_model()
    pending_user = bool(pending_id)

    if pending_user:
        try:
            user = User.objects.get(pk=pending_id, is_active=False)
        except User.DoesNotExist:
            request.session.pop("pending_registration_user_id", None)
            return redirect("user_register")
    elif request.user.is_authenticated:
        user = request.user
    else:
        return redirect("user_register")

    form = RegistrationProfileForm(
        request.POST if request.method == "POST" else None,
        initial={
            "username": user.username if not re.fullmatch(r"user_[0-9a-f]{32}", user.username or "") else "",
            "full_name": user.first_name,
            "major": user.major,
        },
    )
    if request.method == "POST" and form.is_valid():
        user.username = form.cleaned_data["username"]
        user.first_name = form.cleaned_data["full_name"]
        user.major = form.cleaned_data["major"]
        if pending_user:
            user.is_active = True
        try:
            with transaction.atomic():
                update_fields = ["username", "first_name", "major"]
                if pending_user:
                    update_fields.append("is_active")
                user.save(update_fields=update_fields)
        except IntegrityError:
            form.add_error("username", "That username is already in use.")
        else:
            request.session.pop("pending_registration_user_id", None)
            request.session.pop("registration_email", None)
            if pending_user:
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
            return redirect("user_profile:profile")

    return render(request, "login/user_register_profile.html", {"form": form})

def forgot_pwd_page(request):
    return render(request, "login/forgot_pwd.html")
