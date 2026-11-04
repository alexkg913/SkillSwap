from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from .forms import ProfileForm
from .models import Profile

@login_required(login_url="login")
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "user_profile/main_profile.html", {"profile": profile})

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

def security_settings(request):
    return render(request, "user_profile/security_settings.html")
