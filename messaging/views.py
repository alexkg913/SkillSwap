from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q # for complex queries
from .models import DirectMessage

# Create your views here.
@login_required
def inbox(request):
    # Get all messages where the logged-in user is either the sender or receipient. Ordered by descending timestamp.
    user_messages = DirectMessage.objects.filter(Q(sender=request.user) | Q(recipient=request.user)).order_by('-timestamp')

    conversations= {}
    for message in user_messages:
        other_user = message.recipient if message.sender == request.user else message.sender
        if other_user not in conversations:
            conversations[other_user] = []
        conversations[other_user].append(message)

    return render(request, 'messaging/inbox.html', {'conversations': conversations})

