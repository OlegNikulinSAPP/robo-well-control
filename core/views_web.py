import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import plotly.graph_objects as go
import plotly.utils
from .models import Well, PumpCharacteristic, ElectricMotor, TelemetryData, CommandLog


def print_input_statuses_keys(data):
    """Печатает все ключи из секции input_statuses"""
    if not isinstance(data, dict):
        print("data не словарь")
        return

    if 'data' not in data:
        print("Нет ключа 'data'")
        return

    if 'input_statuses' not in data['data']:
        print("Нет секции input_statuses")
        return

    input_statuses = data['data']['input_statuses']

    print("\n=== КЛЮЧИ В input_statuses ===")
    for key in input_statuses.keys():
        print(f"  {key}")

    print(f"\nВсего ключей: {len(input_statuses)}")

def dashboard(request):
    """Главная страница с общей статистикой."""

    # Берем последнюю запись телеметрии
    last = TelemetryData.objects.order_by('-timestamp').first()

    if last and last.raw_data:
        print_input_statuses_keys(last.raw_data)


    context = {
        'wells_count': Well.objects.count(),
        'pumps_count': PumpCharacteristic.objects.count(),
        'motors_count': ElectricMotor.objects.count(),
    }
    return render(request, 'core/dashboard.html', context)


def well_list(request):
    """Список скважин."""
    wells = Well.objects.all()

    # Добавляем статус из телеметрии для каждой скважины
    for well in wells:
        well.status_data = _get_well_status_from_telemetry(well)

    # Расчет статистики
    total_wells = wells.count()
    active_wells = wells.filter(is_active=True).count()
    avg_depth = wells.aggregate(models.Avg('depth'))['depth__avg'] or 0
    avg_depth = round(avg_depth, 1) if avg_depth else 0
    total_debit = wells.aggregate(models.Sum('formation_debit'))['formation_debit__sum'] or 0

    # Получаем поисковый запрос из URL
    search_query = request.GET.get('search', '')

    # Фильтруем скважины по имени
    if search_query:
        wells = wells.filter(name__icontains=search_query)

    context = {
        'wells': wells,
        'total_wells': total_wells,
        'active_wells': active_wells,
        'avg_depth': avg_depth,
        'total_debit': total_debit,

    }

    return render(request, 'core/well_list.html', context)


def well_detail(request, pk):
    """Детальная информация о скважине."""
    well = get_object_or_404(Well, pk=pk)

    # Получаем последнюю телеметрию
    last = well.telemetry.order_by('-timestamp').first()

    # Достаём все секции данных
    if last and last.raw_data:
        raw = last.raw_data
        # Объединяем все секции в один словарь
        registers = {}

        # Собираем из всех возможных секций
        for section in ['input_registers', 'holding_registers', 'coils', 'input_statuses']:
            section_data = raw.get('data', {}).get(section, {})
            registers.update(section_data)
    else:
        registers = {}

    # Список нужных параметров
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

    # Заполняем словарь
    telemetry_data = {}
    for api_key, key in params_map.items():
        if api_key in registers:
            reg = registers[api_key]
            # Если это словарь и есть 'interpreted' - берем его
            if isinstance(reg, dict):
                if 'interpreted' in reg and reg['interpreted'] is not None:
                    telemetry_data[key] = reg['interpreted']
                elif 'raw_value' in reg:
                    # Если нет interpreted, берем raw_value
                    telemetry_data[key] = reg['raw_value']
                else:
                    telemetry_data[key] = None
            else:
                telemetry_data[key] = reg
        else:
            telemetry_data[key] = None

    context = {
        'well': well,
        'telemetry': telemetry_data,
    }

    return render(request, 'core/well_detail.html', context)


def _get_well_status_from_telemetry(well):
    """Вспомогательная функция для получения статуса из телеметрии"""
    last = well.telemetry.order_by('-timestamp').first()

    if last and last.raw_data:
        raw = last.raw_data
        if 'data' in raw and 'input_statuses' in raw['data']:
            status = raw['data']['input_statuses'].get('Состояние ПЭД', {})

    if not last or not last.raw_data:
        return None

    raw = last.raw_data
    if 'data' not in raw:
        return None

    input_statuses = raw['data'].get('input_statuses', {})
    status_info = input_statuses.get('Состояние ПЭД', {})

    if not status_info:
        return None

    result = {
        'is_running': status_info.get('raw_value'),
        'text': status_info.get('interpreted', 'Неизвестно'),
    }

    # Если остановлена - добавляем причину
    if not result['is_running']:
        input_registers = raw['data'].get('input_registers', {})
        stop_info = input_registers.get('Причина последнего отключения', {})
        result['stop_reason'] = stop_info.get('interpreted')
        code = stop_info.get('raw_value')
        result['is_emergency'] = code not in [0, 19, 20, 21] if code is not None else False

    return result

def well_telemetry(request, pk):
    """Страница телеметрии скважины."""
    well = get_object_or_404(Well, pk=pk)
    telemetry = well.telemetry.all()[:20]

    # Получаем выбранную секцию из GET-параметров
    selected_section = request.GET.get('section', 'all')

    # Собираем все параметры из raw_data для последней записи
    all_parameters = {}
    sections = set()  # для сбора уникальных секций

    if telemetry:
        last_record = telemetry[0]

        if last_record.raw_data and 'data' in last_record.raw_data:
            raw_data = last_record.raw_data['data']

            for section_name, section_data in raw_data.items():
                if isinstance(section_data, dict):
                    sections.add(section_name)  # добавляем секцию в список

                    # Если секция выбрана или выбраны все
                    if selected_section == 'all' or selected_section == section_name:
                        for param_name, param_info in section_data.items():
                            all_parameters[f"{section_name}.{param_name}"] = {
                                'section': section_name,
                                'name': param_name,
                                'raw_value': param_info.get('raw_value'),
                                'unit': param_info.get('unit'),
                                'interpreted': param_info.get('interpreted'),
                                'address': param_info.get('address'),
                                'scale_factor': param_info.get('scale_factor'),
                            }

    context = {
        'well': well,
        'telemetry': telemetry,
        'all_parameters': all_parameters,
        'parameters_count': len(all_parameters),
        'sections': sorted(sections),  # передаем список секций в шаблон
        'selected_section': selected_section,
    }

    return render(request, 'core/well_telemetry.html', context)


def well_dashboard(request, pk):
    """Дашборд с графиками телеметрии."""
    well = get_object_or_404(Well, pk=pk)
    return render(request, 'core/well_dashboard.html', {'well': well})


from django.db import models  # добавьте этот импорт вверху файла


def pump_list(request):
    """Список насосов с поиском."""
    pumps = PumpCharacteristic.objects.all()

    # Поиск по параметрам
    search_query = request.GET.get('search', '')
    if search_query:
        pumps = pumps.filter(
            models.Q(harka_stupen__icontains=search_query) |
            models.Q(zavod__icontains=search_query) |
            models.Q(material_stupen__icontains=search_query)
        )

    # Сортировка и ограничение
    pumps = pumps.order_by('harka_stupen')[:50]

    return render(request, 'core/pump_list.html', {'pumps': pumps})


def pump_detail(request, pk):
    """Детальная информация о насосе."""
    pump = get_object_or_404(PumpCharacteristic, pk=pk)
    return render(request, 'core/pump_detail.html', {'pump': pump})


def motor_list(request):
    """Список двигателей."""
    motors = ElectricMotor.objects.all()[:20]
    return render(request, 'core/motor_list.html', {'motors': motors})


def motor_detail(request, pk):
    """Детальная информация о двигателе."""
    motor = get_object_or_404(ElectricMotor, pk=pk)
    return render(request, 'core/motor_detail.html', {'motor': motor})


def pump_chart_data(request, pk):
    """API для получения данных графика насоса."""
    pump = get_object_or_404(PumpCharacteristic, pk=pk)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=pump.q_values,
        y=pump.h_values,
        mode='lines+markers',
        name='Q-H (Напор)',
        line=dict(color='blue', width=2),
        yaxis='y'
    ))

    if pump.n_values:
        fig.add_trace(go.Scatter(
            x=pump.q_values,
            y=pump.n_values,
            mode='lines+markers',
            name='Q-N (Мощность)',
            line=dict(color='red', width=2, dash='dot'),
            yaxis='y2'
        ))

    if pump.kpd_values:
        fig.add_trace(go.Scatter(
            x=pump.q_values,
            y=pump.kpd_values,
            mode='lines+markers',
            name='Q-η (КПД)',
            line=dict(color='green', width=2, dash='dash'),
            yaxis='y3'
        ))

    if pump.nominal_head:
        fig.add_trace(go.Scatter(
            x=[pump.nominal_range],
            y=[pump.nominal_head],
            mode='markers',
            name='Номинальная точка',
            marker=dict(color='gold', size=15, symbol='star'),
            yaxis='y'
        ))

    if pump.left_range and pump.right_range:
        fig.add_vrect(
            x0=float(pump.left_range),
            x1=float(pump.right_range),
            fillcolor="lightgreen",
            opacity=0.2,
            layer="below",
            line_width=0,
            annotation_text="Рабочий диапазон",
            annotation_position="bottom left"
        )

    if pump.optimal_flow_range and len(pump.optimal_flow_range) == 2:
        fig.add_vrect(
            x0=float(pump.optimal_flow_range[0]),
            x1=float(pump.optimal_flow_range[1]),
            fillcolor="yellow",
            opacity=0.2,
            layer="below",
            line_width=0,
            annotation_text="Оптимальный диапазон",
            annotation_position="top left"
        )

    fig.update_layout(
        title=f"Характеристики насоса {pump.harka_stupen}",
        xaxis=dict(title="Подача Q, м³/сут", domain=[0, 0.9]),
        yaxis=dict(title="Напор H, м", title_font=dict(color="blue"), tickfont=dict(color="blue")),
        yaxis2=dict(
            title="Мощность N, кВт",
            title_font=dict(color="red"),
            tickfont=dict(color="red"),
            anchor="x",
            overlaying="y",
            side="right",
            position=0.95
        ),
        yaxis3=dict(
            title="КПД η, %",
            title_font=dict(color="green"),
            tickfont=dict(color="green"),
            anchor="free",
            overlaying="y",
            side="right",
            position=1.0
        ),
        hovermode='x unified',
        template='plotly_white'
    )

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return JsonResponse({'graph': graph_json})


def motor_chart_data(request, pk):
    """API для получения данных графика двигателя."""
    motor = get_object_or_404(ElectricMotor, pk=pk)

    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=motor.vibration_level,
        title={'text': f"Вибрация {motor.model}<br><span style='font-size:0.8em;color:gray'>мм/с</span>"},
        delta={'reference': 4.5},
        gauge={
            'axis': {'range': [0, 20]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 2.8], 'color': "lightgreen"},
                {'range': [2.8, 4.5], 'color': "lightblue"},
                {'range': [4.5, 7.1], 'color': "yellow"},
                {'range': [7.1, 20], 'color': "salmon"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 7.1
            }
        }
    ))

    fig.update_layout(width=600, height=400)
    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return JsonResponse({'graph': graph_json})


def telemetry_chart_data(request, pk):
    """API для дашборда."""
    well = get_object_or_404(Well, pk=pk)

    # Последние данные
    if request.GET.get('latest'):
        last = well.telemetry.first()
        if last:
            return JsonResponse({
                'latest': {
                    'pressure': last.intake_pressure,
                    'temperature': last.intake_temperature,
                    'vib_x': last.vibration_x,
                    'vib_y': last.vibration_y,
                }
            })
        return JsonResponse({'latest': None})

    # Данные для графиков
    telemetry = well.telemetry.all()[:100]

    print(f"Найдено записей телеметрии для скважины {well.name}: {len(telemetry)}")

    # Если нет данных - вернем тестовые с пояснением
    if not telemetry:
        print("Нет данных телеметрии! Используем тестовые данные")
        return JsonResponse({
            'charts': {
                'pressure_temp': {
                    'data': [
                        {'x': [1, 2, 3], 'y': [10, 20, 15], 'type': 'scatter', 'name': 'Давление (тест)',
                         'line': {'color': 'blue'}},
                        {'x': [1, 2, 3], 'y': [30, 40, 35], 'type': 'scatter', 'name': 'Температура (тест)',
                         'yaxis': 'y2', 'line': {'color': 'red'}}
                    ],
                    'layout': {
                        'title': 'Нет данных телеметрии (тестовые данные)',
                        'yaxis': {'title': 'Давление, атм'},
                        'yaxis2': {'title': 'Температура, °C', 'overlaying': 'y', 'side': 'right'}
                    }
                },
                'currents': {
                    'data': [
                        {'x': [1, 2, 3], 'y': [5, 6, 7], 'type': 'scatter', 'name': 'Фаза A'},
                        {'x': [1, 2, 3], 'y': [5, 6, 7], 'type': 'scatter', 'name': 'Фаза B'},
                        {'x': [1, 2, 3], 'y': [5, 6, 7], 'type': 'scatter', 'name': 'Фаза C'}
                    ],
                    'layout': {'title': 'Нет данных токов (тест)'}
                },
                'vibration': {
                    'data': [
                        {'x': [1, 2, 3], 'y': [0.5, 0.6, 0.7], 'type': 'scatter', 'name': 'Ось X'},
                        {'x': [1, 2, 3], 'y': [0.5, 0.6, 0.7], 'type': 'scatter', 'name': 'Ось Y'}
                    ],
                    'layout': {'title': 'Нет данных вибрации (тест)'}
                },
                'power': {
                    'data': [
                        {'x': [1, 2, 3], 'y': [1, 2, 1.5], 'type': 'scatter', 'name': 'Мощность',
                         'line': {'color': 'green'}}
                    ],
                    'layout': {'title': 'Нет данных мощности (тест)'}
                }
            }
        })

    # Формируем реальные данные
    print(f"Формируем графики из {len(telemetry)} записей")

    # Подготовка данных
    timestamps = [t.timestamp for t in telemetry]

    charts = {
        'pressure_temp': {
            'data': [
                {
                    'x': timestamps,
                    'y': [t.intake_pressure for t in telemetry],
                    'type': 'scatter',
                    'name': 'Давление на приеме',
                    'line': {'color': 'blue'}
                },
                {
                    'x': timestamps,
                    'y': [t.intake_temperature for t in telemetry],
                    'type': 'scatter',
                    'name': 'Температура',
                    'yaxis': 'y2',
                    'line': {'color': 'red'}
                }
            ],
            'layout': {
                'title': 'Давление и температура',
                'yaxis': {'title': 'Давление, атм'},
                'yaxis2': {'title': 'Температура, °C', 'overlaying': 'y', 'side': 'right'}
            }
        },
        'currents': {
            'data': [
                {
                    'x': timestamps,
                    'y': [t.current_phase_a for t in telemetry],
                    'type': 'scatter',
                    'name': 'Фаза A'
                },
                {
                    'x': timestamps,
                    'y': [t.current_phase_b for t in telemetry],
                    'type': 'scatter',
                    'name': 'Фаза B'
                },
                {
                    'x': timestamps,
                    'y': [t.current_phase_c for t in telemetry],
                    'type': 'scatter',
                    'name': 'Фаза C'
                }
            ],
            'layout': {'title': 'Токи фаз', 'yaxis': {'title': 'Ток, А'}}
        },
        'vibration': {
            'data': [
                {
                    'x': timestamps,
                    'y': [t.vibration_x for t in telemetry],
                    'type': 'scatter',
                    'name': 'Ось X'
                },
                {
                    'x': timestamps,
                    'y': [t.vibration_y for t in telemetry],
                    'type': 'scatter',
                    'name': 'Ось Y'
                }
            ],
            'layout': {'title': 'Вибрация', 'yaxis': {'title': 'мм/с'}}
        },
        'power': {
            'data': [
                {
                    'x': timestamps,
                    'y': [t.active_power for t in telemetry],
                    'type': 'scatter',
                    'name': 'Активная мощность',
                    'line': {'color': 'green'}
                }
            ],
            'layout': {'title': 'Мощность', 'yaxis': {'title': 'кВт'}}
        }
    }

    return JsonResponse({'charts': charts})


def command_logs(request):
    """Страница истории команд."""
    logs = CommandLog.objects.all().select_related('well')[:100]
    return render(request, 'core/command_logs.html', {'logs': logs})


def equipment_select(request):
    """Страница выбора оборудования"""
    wells = Well.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/equipment_select.html', {'wells': wells})
