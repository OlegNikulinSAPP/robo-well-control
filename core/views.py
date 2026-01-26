from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Well
from .serializers import WellSerializer


class WellViewSet(viewsets.ModelViewSet):
    """
    ViewSet для обработки операций CRUD с моделью Well.

    Предоставляет полный REST API для управления скважинами:
    - GET /api/wells/ - список всех скважин
    - POST /api/wells/ - создание новой скважины
    - GET /api/wells/{id}/ - детализация скважины
    - PUT /api/wells/{id}/ - полное обновление
    - PATCH /api/wells/{id}/ - частичное обновление
    - DELETE /api/wells/{id}/ - удаление скважины
    """
    queryset = Well.objects.all()
    serializer_class = WellSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Получение QuerySet с возможностью фильтрации.

        Returns:
            QuerySet: Отфильтрованный набор скважин
        """
        queryset = super().get_queryset()

        # Фильтрация по глубине (пример: ?min_depth=1000)
        min_depth = self.request.query_params.get('min_depth')
        max_depth = self.request.query_params.get('max_depth')

        if min_depth:
            queryset = queryset.filter(depth__gte=float(min_depth))
        if max_depth:
            queryset = queryset.filter(depth__lte=float(max_depth))

        return queryset.order_by('name')

    @action(detail=True, methods=['get'])
    def telemetry(self, request, pk=None):
        """
        Эндпоинт для получения телеметрии скважины.

        Args:
            request: HTTP запрос
            pk: ID скважины

        Returns:
            Response: Телеметрия скважины
        """
        well = self.get_object()
        # TODO: Реализовать получение реальной телеметрии
        telemetry_data = {
            'well_id': well.id,
            'well_name': well.name,
            'status': 'active',
            'current_frequency': 50.0,
            'current_pressure': 15.5,
            'current_temperature': 85.0,
            'timestamp': '2024-01-15T10:30:00Z'
        }
        return Response(telemetry_data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Статистика по всем скважинам.

        Args:
            request: HTTP запрос

        Returns:
            Response: Статистические данные
        """
        wells = self.get_queryset()
        stats = {
            'total_wells': wells.count(),
            'avg_depth': wells.aggregate(models.Avg('depth'))['depth__avg'] if wells.exists() else 0,
            'max_depth': wells.aggregate(models.Max('depth'))['depth__max'] if wells.exists() else 0,
            'min_depth': wells.aggregate(models.Min('depth'))['depth__min'] if wells.exists() else 0,
            'total_debit': wells.aggregate(models.Sum('formation_debit'))[
                'formation_debit__sum'] if wells.exists() else 0
        }
        return Response(stats)

    def perform_create(self, serializer):
        """
        Дополнительные действия при создании скважины.

        Args:
            serializer: Сериализатор с данными
        """
        serializer.save()
        # TODO: Логирование, уведомления и т.д.

    def perform_destroy(self, instance):
        """
        Дополнительные действия при удалении скважины.

        Args:
            instance: Удаляемый объект
        """
        # TODO: Проверка зависимостей, логирование
        instance.delete()
