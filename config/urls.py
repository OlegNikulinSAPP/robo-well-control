"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path  # вместо url используем re_path
# from .swagger import schema_view
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('', include('core.urls_web')),

    # Swagger документация
    # re_path(r'^swagger(?P<format>\.json|\.yaml)$',
    #         schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # path('swagger/', schema_view.with_ui('swagger', cache_timeout=0),
    #      name='schema-swagger-ui'),
    # path('redoc/', schema_view.with_ui('redoc', cache_timeout=0),
    #      name='schema-redoc'),
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
