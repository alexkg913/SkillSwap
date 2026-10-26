from django.http import request
from django.contrib.auth.decorators import login_required
from django.db.models import Q # for complex queries
from .models import DirectMessage
from django.shortcuts import get_object_or_404, redirect, render


# Create your views here.
@login_required(login_url='/login/') # Decorator ensures that only users who are logged in can access the inbox view.
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
User = get_user_model() # Get the user model that is currently active in this project. This is useful if you have a custom user model.

@login_required(login_url='/login/') # Decorator ensures that only users who are logged in can access the thread view.
def thread(request, user_id):
    other_user = get_object_or_404(User, pk=user_id) # Get the other user in the conversation or return a 404 error if they don't exist.

    if other_user == request.user:
        return redirect('inbox')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip() # Get the content of the message from the POST request and remove leading/trailing whitespace.
        if content:
            DirectMessage.objects.create(sender=request.user, recipient=other_user, content=content)
        return redirect('thread', user_id=other_user.id)

    thread_messages = DirectMessage.objects.filter( # Retrieve all messages in the conversation between the logged-in user and the other user, ordered by timestamp.
        Q(sender=request.user, recipient=other_user) |
        Q(sender=other_user, recipient=request.user)
    ).order_by('timestamp')
    return render(request, 'messaging/thread.html', {
        'other_user': other_user,
        'thread_messages': thread_messages,
    })