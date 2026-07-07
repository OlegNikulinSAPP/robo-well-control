from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('', csrf_exempt(admin.site.urls)),
]