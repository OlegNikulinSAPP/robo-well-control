from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import PumpCharacteristic
from .serializers_pump import PumpCharacteristicSerializer, PumpCharacteristicListSerializer


class PumpCharacteristicViewSet(viewsets.ModelViewSet):
    """
    ViewSet для обработки операций CRUD с характеристиками насосов ЭЦН.
    """
