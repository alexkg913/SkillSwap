import re

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from login.choices import FSC_MAJOR_CHOICES
from login.views import ResetPasswordForm

from .forms import FSC_CLUB_CHOICES, ProfileForm, SKILL_CHOICES
from .models import Profile
from .club_catalog import search_clubs, suggested_clubs
from .skill_catalog import search_skills, suggested_skills

@login_required(login_url="login")
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    clubs = [name.strip() for name in re.split(r"[\r\n,]+", profile.interests_clubs or "") if name.strip()]
    return render(request, "user_profile/main_profile.html", {"profile": profile, "clubs": clubs})

@login_required(login_url="login")
def user_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(
        request.POST or None,
        request.FILES or None,
        instance=profile,
        initial={"major": request.user.major},
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        request.user.major = form.cleaned_data["major"]
        request.user.save(update_fields=["major"])
        return redirect("user_profile:user_settings")

    return render(request, "user_profile/user_settings.html", {"form": form})


@login_required(login_url="login")
@never_cache
def skill_options(request):
    major = request.GET.get("major", "")
    if major not in dict(FSC_MAJOR_CHOICES):
        return JsonResponse({"error": "Select a valid major."}, status=400)

    query = request.GET.get("q", "").strip()[:80]
    if query:
        results = search_skills(query)
        legacy = [name for name, _ in SKILL_CHOICES if query.casefold() in name.casefold()]
        skills = list(dict.fromkeys([*results, *legacy]))[:12]
    else:
        skills = suggested_skills(major, request.user.username)
    return JsonResponse({"skills": skills})


@login_required(login_url="login")
@never_cache
def club_options(request):
    major = request.GET.get("major", "")
    if major not in dict(FSC_MAJOR_CHOICES):
        return JsonResponse({"error": "Select a valid major."}, status=400)

    query = request.GET.get("q", "").strip()[:80]
    clubs = (search_clubs(query, FSC_CLUB_CHOICES) if query else
             suggested_clubs(major, request.user.username, FSC_CLUB_CHOICES))
    return JsonResponse({"clubs": clubs})

@login_required(login_url="login")
@sensitive_post_parameters("password", "password_confirm")
@never_cache
def security_settings(request):
    form = ResetPasswordForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            validate_password(form.cleaned_data["password"], user=request.user)
        except ValidationError as errors:
            form.add_error("password", errors)
        else:
            request.user.set_password(form.cleaned_data["password"])
            request.user.save(update_fields=["password"])
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been changed.")
            return redirect("user_profile:security_settings")

    return render(request, "user_profile/security_settings.html", {"form": form})
