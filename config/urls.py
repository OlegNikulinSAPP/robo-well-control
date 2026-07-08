from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # ← БЕЗ csrf_exempt!
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),
]
