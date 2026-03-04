from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import WellViewSet, AlertViewSet, CommandLogViewSet
from .views_pumps import PumpCharacteristicViewSet
from .views_motors import ElectricMotorViewSet  # Добавляем импорт

from .views import TelemetryViewSet
from .views import ControlViewSet

# Создаем router для автоматической генерации URL
router = DefaultRouter()
router.register(r'wells', WellViewSet, basename='well')
router.register(r'pumps', PumpCharacteristicViewSet, basename='pump')
router.register(r'motors', ElectricMotorViewSet, basename='motor')  # Добавляем
router.register(r'telemetry', TelemetryViewSet, basename='telemetry')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'command-logs', CommandLogViewSet, basename='command-log')
router.register(r'control', ControlViewSet, basename='control')

# Паттерны URL для приложения core
urlpatterns = [
    path('', include(router.urls)),
    path('chat/', views.chat_api, name='chat_api'),
]
