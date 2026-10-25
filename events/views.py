from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from home.views import map_config

from .forms import TutoringEventForm
from .models import TutoringEvent
from .selectors import campus_building_coordinates


def picker_map_config():
    """Map configuration for the picker.

    The home page's config plus the campus bounding box, which the picker uses
    to warn about an off-campus pin. It is added here rather than in
    home.views.map_config() so the home page's payload keeps the exact shape
    its tests pin down -- and the bbox is only advisory in the browser anyway,
    since TutoringEventForm re-checks it server-side.
    """
    config = map_config()
    config["campus_bbox"] = list(settings.SKILLSWAP_CAMPUS_BBOX)
    return config


def _form_context(form, heading, event):
    return {
        "form": form,
        "heading": heading,
        "event": event,
        "map_config": picker_map_config(),
        "campus_buildings": campus_building_coordinates(),
    }


def _hosted_by(request, pk):
    """Fetch an event the signed-in user hosts, or 404.

    Object-level permission: being authenticated is not enough. Filtering on
    host in the lookup means a non-owner gets a 404 and cannot even confirm
    the event exists.
    """
    return get_object_or_404(TutoringEvent, pk=pk, host=request.user)


@login_required
def create_event(request):
    if request.method == "POST":
        form = TutoringEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            # Ownership comes from the session, never from submitted data.
            event.host = request.user
            event.save()
            return redirect(reverse("home:index"))
    else:
        form = TutoringEventForm()

    return render(
        request,
        "events/event_form.html",
        _form_context(form, "Create a tutoring event", None),
    )


@login_required
def edit_event(request, pk):
    event = _hosted_by(request, pk)

    if request.method == "POST":
        form = TutoringEventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect(reverse("home:index"))
    else:
        form = TutoringEventForm(instance=event)

    return render(
        request,
        "events/event_form.html",
        _form_context(form, "Edit tutoring event", event),
    )


@login_required
@require_POST
def cancel_event(request, pk):
    """Cancel an event. POST only, and never a row delete."""
    event = _hosted_by(request, pk)
    event.is_cancelled = True
    event.save(update_fields=["is_cancelled"])
    return redirect(reverse("home:index"))
