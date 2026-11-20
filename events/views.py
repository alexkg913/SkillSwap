from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from home.views import map_config

from .forms import TutoringEventForm
from .models import TutoringEvent, EventInteraction
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

def find_tutor(request):
    return render(request, "events/find_tutor.html")

def be_tutor(request):
    return render(request, "events/be_tutor.html")

@login_required
def saved_events(request):
    interactions = (
        EventInteraction.objects
        .filter(saved=True, student=request.user, tutoring_event__is_cancelled=False)
        .select_related("tutoring_event")
    )
    events = (
            TutoringEvent.objects
            .filter(host=request.user, is_cancelled=False)
        )
    
    return render(request, "events/saved_events.html", {
        "saved_events": interactions,
        "my_events": events
    })


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
    return redirect(reverse("events:saved_events"))


def _toggle_interaction(request, event_id, field):
    event = get_object_or_404(
        TutoringEvent, pk=event_id, isPublic=True, is_cancelled=False
    )
    with transaction.atomic():
        interaction, _ = EventInteraction.objects.select_for_update().get_or_create(
            tutoring_event=event,
            student=request.user,
        )
        # Flip in the database rather than saving a potentially stale value.
        EventInteraction.objects.filter(pk=interaction.pk).update(**{field: ~F(field)})
    return redirect("home:index")


@login_required
@require_POST
def rsvp_event(request, event_id):
    return _toggle_interaction(request, event_id, "going")


@login_required
@require_POST
def save_event(request, event_id):
    return _toggle_interaction(request, event_id, "saved")
