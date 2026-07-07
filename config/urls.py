from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static

# Правильный способ обернуть админку в csrf_exempt
urlpatterns = [
    path('admin/', csrf_exempt(admin.site.urls)),
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),
]

# Добавляем обслуживание статики для всех случаев
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
