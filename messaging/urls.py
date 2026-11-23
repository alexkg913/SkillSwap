from django.urls import path
from . import views
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('thread/<uuid:user_id>/', views.thread, name='thread'),

    path('new/', views.new_conversation, name='new_conversation'),
    path('event_chat/<int:event_id>/', views.event_chat, name='event_chat'),
    path('event_chats/', views.event_chats, name='event_chats'),
]