from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

# Правильный способ обернуть админку в csrf_exempt
urlpatterns = [
    path('admin/', csrf_exempt(admin.site.urls)),  # ← ТАК ПРАВИЛЬНО!
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),
]
