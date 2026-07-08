from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

# Правильный способ обернуть админку
admin_site = admin.site
admin_site.login = csrf_exempt(admin_site.login)

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),
]
