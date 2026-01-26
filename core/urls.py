from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WellViewSet

# Создаем router для автоматической генерации URL
router = DefaultRouter()
router.register(r'wells', WellViewSet, basename='well')

# Паттерны URL для приложения core
urlpatterns = [
    path('', include(router.urls)),
]