from django.shortcuts import render
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

