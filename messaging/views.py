from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Q # for complex queries
from .models import DirectMessage
from django.core.exceptions import PermissionDenied # for handling unauthorized access
from .models import DirectMessage, EventMessage # for handling event messages
from events.models import EventInteraction, TutoringEvent # for handling event messages


# Create your views here.
@login_required # Decorator ensures that only users who are logged in can access the inbox view.
# The inbox view retrieves all messages where the logged-in user is either the sender or recipient, groups them by the other user in the conversation, and renders them in the 'messaging/inbox.html' template.
def inbox(request):
    # Get all messages where the logged-in user is either the sender or recipient. Ordered by descending timestamp.
    user_messages = DirectMessage.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).order_by('-timestamp')

    conversations= {}
    # Group messages by the other user in the conversation
    for message in user_messages:
        other_user = message.recipient if message.sender == request.user else message.sender
        if other_user not in conversations:
            conversations[other_user] = []
        conversations[other_user].append(message)

    return render(request, 'messaging/inbox.html', {'conversations': conversations})



from django.contrib.auth import get_user_model
User = get_user_model()

@login_required
def thread(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    thread_messages = DirectMessage.objects.filter(
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).order_by('timestamp')
    return render(request, 'messaging/thread.html', {
        'other_user': other_user,
        'thread_messages': thread_messages,
    })


@login_required(login_url='/login/')
def event_chat(request, event_id):
    event = get_object_or_404(TutoringEvent, id=event_id)

    is_host = event.host == request.user.id # Check if the logged-in user is the host of the event
    is_going = EventInteraction.objects.filter(
        tutoring_event=event, student=request.user, statues=EventInteraction.Statuses.GOING).exists() # Check if the logged-in user is going to the event

    if not (is_host or is_going):
        raise PermissionDenied("You do not have permission to view this event chat.") # Raise a permission denied error if the user is neither the host nor going to the event

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            EventMessage.objects.create(event=event, sender=request.user, content=content) # Create a new event message if the content is not empty

            return redirect('event_chat', event_id=event.id) #Redirect the samne page to show the new message

    event_messages = EventMessage.objects.filter(event=event).order_by('timestamp') # Get all messages for the event, ordered by timestamp
    return render(request, 'messaging/event_chat.html', {
        'event': event,
        'event_messages': event_messages,
    })