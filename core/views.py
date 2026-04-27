from datetime import timedelta, timezone, datetime

from django.db import models
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action

from .ai_assistant import RoboWellAssistant
from .models import Well, CommandLog
from .serializers import WellSerializer, AlertSerializer, CommandLogSerializer, WellListSerializer, \
    WellDetailSerializer
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
    queryset = Well.objects.all()  # noqa
    serializer_class = WellSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':  # noqa
            return WellListSerializer  # для списка - краткий
        elif self.action == 'retrieve':  # noqa
            return WellDetailSerializer  # для детального просмотра - полный
        return WellSerializer  # для create/update - базовый

    def get_queryset(self):
        """Опционально: фильтрация активных скважин по умолчанию"""
        queryset = Well.objects.all()  # noqa
        # Только активные скважины, если не запрошены все
        if self.request.query_params.get('include_inactive') != 'true':
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=['get'])
    def calculations(self, request, pk=None):
        """
        Получить расчетные параметры для скважины
        GET /api/wells/1/calculations/?target_flow=150
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

    @action(detail=True, methods=['get'])
    def full_report(self, request, pk=None):
        """
        Полный инженерный отчет по скважине
        GET /api/wells/1/full_report/?target_flow=200
        """
        well = self.get_object()

        # Получаем параметры из запроса
        target_flow = request.query_params.get('target_flow')
        intake_pressure = request.query_params.get('intake_pressure')

        # Преобразуем в числа, если переданы
        if target_flow:
            try:
                target_flow = float(target_flow)
            except ValueError:
                return Response(
                    {'error': 'Некорректный целевой расход'},
                    status=400
                )

        if intake_pressure:
            try:
                intake_pressure = float(intake_pressure)
            except ValueError:
                return Response(
                    {'error': 'Некорректное давление на приеме'},
                    status=400
                )

        # Получаем полный отчет
        try:
            report = well.get_full_engineering_report(
                target_flow=target_flow,
                intake_pressure=intake_pressure
            )
            return Response(report)
        except Exception as e:
            return Response(
                {'error': f'Ошибка при расчете: {str(e)}'},
                status=500
            )

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
    serializer_class = TelemetrySerializer  # стандартный для списка
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['well']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Последние данные для каждой скважины (как в well_detail)."""
        well_id = request.query_params.get('well')

        try:
            if well_id:
                # Получаем последнюю телеметрию
                data = TelemetryData.objects.filter(well_id=well_id).first()

                if not data:
                    return Response({'error': 'No telemetry data'}, status=404)

                # Собираем данные из raw_data (как в well_detail)
                registers = {}
                if data.raw_data:
                    raw = data.raw_data
                    for section in ['input_registers', 'holding_registers', 'coils', 'input_statuses']:
                        section_data = raw.get('data', {}).get(section, {})
                        registers.update(section_data)

                # Список нужных параметров (как в well_detail)
                params_map = {
                    # Токи
                    'Полный ток двигателя фазы А': 'current_a',
                    'Полный ток двигателя фазы B': 'current_b',
                    'Полный ток двигателя фазы C': 'current_c',
                    'Максимальный ток по фазам': 'max_current',

                    # Напряжение и мощность
                    'Среднее фазное напряжение': 'avg_voltage',
                    'Полная мощность на двигателе': 'apparent_power',
                    'Активная мощность': 'active_power',

                    # Электрические параметры
                    'Сопротивление изоляции': 'insulation_resistance',
                    'Cos φ двигателя ': 'power_factor',
                    'Загрузка': 'load_percent',

                    # Баланс
                    'Дисбаланс токов': 'current_unbalance',
                    'Дисбаланс напряжений': 'voltage_unbalance',

                    # Давление и температура
                    'Давление на приеме насоса': 'intake_pressure',
                    'Температура жидкости на приеме насоса': 'intake_temperature',
                    'Температура двигателя': 'motor_temperature',

                    # Вибрация
                    'Вибрация по оси X': 'vibration_x',
                    'Вибрация по оси Y': 'vibration_y',
                    'Вибрация по оси Z': 'vibration_z',

                    # Давление в буфере и частота
                    'Давление в буфере': 'buffer_pressure',
                    'Частота питания ПЭД': 'frequency',

                    # Состояния
                    'Состояние переключателя': 'switch_state',
                    'Причина последнего отключения': 'stop_reason',
                    'Вид последнего запуска': 'last_start_type',

                    # Дополнительные параметры
                    'Давление на выкиде': 'discharge_pressure',
                    'Температура жидкости на приеме': 'fluid_temperature',
                    'Температура ключей ПЧ': 'inverter_temp',

                    # Даты
                    'Дата/время последнего включения': 'last_start_time',
                    'Дата/время последнего отключения': 'last_stop_time',

                    "Состояние ПЭД": "is_running",
                }

                # Заполняем словарь (как в well_detail)
                telemetry_data = {}
                for api_key, key in params_map.items():
                    if api_key in registers:
                        reg = registers[api_key]
                        if isinstance(reg, dict):
                            if 'interpreted' in reg and reg['interpreted'] is not None:
                                telemetry_data[key] = reg['interpreted']
                            elif 'raw_value' in reg:
                                telemetry_data[key] = reg['raw_value']
                            else:
                                telemetry_data[key] = None
                        else:
                            telemetry_data[key] = reg
                    else:
                        telemetry_data[key] = None

                # Добавляем базовую информацию
                telemetry_data['id'] = data.id
                telemetry_data['well_name'] = data.well.name if data.well else None
                telemetry_data['timestamp'] = data.timestamp
                # telemetry_data['is_running'] = False
                #
                # # Определяем статус работы
                # freq = telemetry_data.get('frequency', '0')
                # try:
                #     if freq and float(freq) > 0.5:
                #         telemetry_data['is_running'] = True
                # except:
                #     pass

                return Response(telemetry_data)

        except Exception as e:
            print(f"Error in latest: {e}")
            return Response({'error': str(e)}, status=500)

        # Для всех скважин (если well_id не указан)
        result = []
        for well in Well.objects.all():
            last = well.telemetry.first()
            if last:
                result.append({
                    'id': last.id,
                    'well_name': well.name,
                    'timestamp': last.timestamp,
                })
        return Response(result)


    # @action(detail=False, methods=['get'])
    # def latest(self, request):
    #     well_id = request.query_params.get('well')
    #
    #     if well_id:
    #         print(f"\n🔍🔍🔍 LATTEST CALL для well_id={well_id} 🔍🔍🔍")
    #
    #         # 1. Сколько всего записей?
    #         total = TelemetryData.objects.filter(well_id=well_id).count()
    #         print(f"1. Всего записей в БД: {total}")
    #
    #         # 2. Все записи с сортировкой (первые 10)
    #         print("2. Все записи (отсортированные по -timestamp):")
    #         all_records = TelemetryData.objects.filter(
    #             well_id=well_id
    #         ).order_by('-timestamp')[:10]
    #
    #         for i, rec in enumerate(all_records):
    #             print(f"   {i + 1}. ID:{rec.id} | время:{rec.timestamp} | давление:{rec.intake_pressure}")
    #
    #         # 3. Берем первую
    #         data = all_records.first() if all_records else None
    #         print(f"3. FIRST: ID:{data.id if data else 'None'} время:{data.timestamp if data else 'None'}")
    #
    #         # 4. Сериализуем
    #         serializer = self.get_serializer(data)
    #         response_data = serializer.data
    #         print(f"4. Сериализовано: {response_data.get('id')} время:{response_data.get('timestamp')}")
    #
    #         return Response(response_data)
    #
    #     # Для всех скважин
    #     wells = Well.objects.all()
    #     result = []
    #     for well in wells:
    #         last = TelemetryData.objects.filter(well=well).order_by('-timestamp').first()
    #         if last:
    #             result.append(self.get_serializer(last).data)
    #     return Response(result)

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
