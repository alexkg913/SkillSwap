from django.urls import path
from . import views
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('thread/<uuid:user_id>/', views.thread, name='thread'),
]