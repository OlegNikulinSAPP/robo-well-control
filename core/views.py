from datetime import timedelta, timezone, datetime

from django.db import models
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from .ai_assistant import RoboWellAssistant
from .models import Well, CommandLog
from .serializers import WellSerializer, AlertSerializer, CommandLogSerializer, WellListSerializer, WellDetailSerializer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import TelemetryData
from .serializers import TelemetrySerializer
from .models import Alert

from rest_framework import viewsets, permissions, status, filters
from django_filters.rest_framework import DjangoFilterBackend

from .services.control_service import ControlService


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('question')

        # Здесь вызывай твоего ассистента
        assistant = RoboWellAssistant()
        answer = assistant.ask(question)

        return JsonResponse({'answer': answer})


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

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return WellListSerializer  # для списка - краткий
        elif self.action == 'retrieve':
            return WellDetailSerializer  # для детального просмотра - полный
        return WellSerializer  # для create/update - базовый

    @action(detail=True, methods=['get'])
    def calculations(self, request, pk=None):
        """
        Получить расчетные параметры для скважины
        """
        well = self.get_object()
        target_flow = request.query_params.get('target_flow')

        if target_flow:
            try:
                target_flow = float(target_flow)
            except ValueError:
                return Response(
                    {'error': 'Некорректный расход'},
                    status=400
                )

        # Используем сериализатор с контекстом
        serializer = WellDetailSerializer(
            well,
            context={'target_flow': target_flow, 'request': request}
        )
        return Response(serializer.data)

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
        Получить последние данные телеметрии для скважины.
        """
        well = self.get_object()  # ← получаем скважину по ID
        latest = well.telemetry.first()  # ← берем последнюю запись телеметрии

        if latest:
            serializer = TelemetrySerializer(latest)  # ← сериализуем
            return Response(serializer.data)
        return Response({'detail': 'Данные телеметрии отсутствуют'}, status=404)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Получение исторических данных по телеметрии для скважины
        """
        well = self.get_object()

        # Получаем параметр hours из запроса (по умолчанию 24)
        hours = int(request.query_params.get('hours', 24))

        # Вычисляем временную границу
        time_threshold = datetime.now() - timedelta(hours=hours)

        # Фильтруем записи новее этой границы
        telemetry = well.telemetry.filter(timestamp__gte=time_threshold)

        # Пагинация
        page = self.paginate_queryset(telemetry)
        if page is not None:
            serializer = TelemetrySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Если без пагинации
        serializer = TelemetrySerializer(telemetry, many=True)
        return Response(serializer.data)

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


class TelemetryViewSet(viewsets.ModelViewSet):
    """API для работы с телеметрией."""
    queryset = TelemetryData.objects.all()
    serializer_class = TelemetrySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]  # Только эти два
    filterset_fields = ['well']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Последние данные для каждой скважины."""
        well_id = request.query_params.get('well')
        if well_id:
            data = TelemetryData.objects.filter(well_id=well_id).first()
            serializer = self.get_serializer(data)
            return Response(serializer.data)

        # Последние данные для всех скважин
        wells = Well.objects.all()
        result = []
        for well in wells:
            last = well.telemetry.first()
            if last:
                result.append(self.get_serializer(last).data)
        return Response(result)

    @action(detail=False, methods=['get'])
    def range(self, request):
        """Данные за период."""
        well_id = request.query_params.get('well')
        hours = int(request.query_params.get('hours', 24))

        if not well_id:
            return Response({'error': 'well parameter required'}, status=400)

        time_threshold = datetime.now() - timedelta(hours=hours)
        data = TelemetryData.objects.filter(
            well_id=well_id,
            timestamp__gte=time_threshold
        ).order_by('timestamp')

        page = self.paginate_queryset(data)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)


from .models import Alert


class AlertViewSet(viewsets.ModelViewSet):
    """API для уведомлений."""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['well', 'severity', 'is_read']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Отметить уведомления как прочитанные."""
        alert_ids = request.data.get('alert_ids', [])
        Alert.objects.filter(id__in=alert_ids).update(is_read=True)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Количество непрочитанных уведомлений."""
        count = Alert.objects.filter(is_read=False).count()
        return Response({'count': count})


class CommandLogViewSet(viewsets.ModelViewSet):
    """API для просмотра логов команд."""
    queryset = CommandLog.objects.all()
    serializer_class = CommandLogSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['well', 'command_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def by_well(self, request):
        """Логи по конкретной скважине."""
        well_id = request.query_params.get('well_id')
        if well_id:
            logs = self.queryset.filter(well_id=well_id)
            page = self.paginate_queryset(logs)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response({'error': 'well_id required'}, status=400)


class ControlViewSet(viewsets.ViewSet):
    """API для управления оборудованием."""

    @action(detail=False, methods=['post'])
    def adjust_frequency(self, request):
        """Изменение частоты для скважины."""
        well_id = request.data.get('well_id')
        frequency = request.data.get('frequency')

        if not well_id or not frequency:
            return Response(
                {'error': 'well_id и frequency обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ControlService()
        result = service.set_frequency(well_id, frequency)

        if result.get('status') == 'success':
            return Response(result)
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def optimal(self, request):
        """Получение оптимальной частоты для скважины."""
        well_id = request.query_params.get('well_id')

        if not well_id:
            return Response(
                {'error': 'well_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = ControlService()
        freq = service.calculate_optimal_frequency(well_id)

        return Response({
            'well_id': well_id,
            'optimal_frequency': freq,
            'unit': 'Hz'
        })
