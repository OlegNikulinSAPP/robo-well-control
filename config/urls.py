from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

# Оборачиваем всю админку в csrf_exempt
admin.site.urls = csrf_exempt(admin.site.urls)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),
]
