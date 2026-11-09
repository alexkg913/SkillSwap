from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.db.models import Q # for complex queries
from .models import DirectMessage


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