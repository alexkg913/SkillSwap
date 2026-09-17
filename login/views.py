from django.shortcuts import render
from django.http import HttpResponse

def login_page(request):
    return HttpResponse("This should be the first login page user sees")
