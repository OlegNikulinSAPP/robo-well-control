"""
ИИ-ассистент для системы RoboWell Control System.
Позволяет работать со скважинами, насосами и двигателями через API,
а также отвечает на инженерные вопросы, используя документацию проекта.
"""

import openai
import requests
import json
import re
import socket
import urllib3
from typing import Optional, Dict, Any, List
import time

# Отключаем предупреждения о непроверенных SSL сертификатах (если нужно)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== НАСТРОЙКИ ====================

# Настройки подключения к polza.ai
OPENAI_API_KEY = "pza_EoYwPLwMlwyQPbBcOQcVxsNQtoyEPzmn"
OPENAI_API_URL = "https://api.polza.ai/v1"

# Настройки подключения к API проекта
API_BASE_URL = "http://127.0.0.1:8000/api"

# Глобальный таймаут для всех запросов
DEFAULT_TIMEOUT = 10  # секунд


# Настраиваем сессию с таймаутами
class TimeoutAdapter(requests.adapters.HTTPAdapter):
    def send(self, request, **kwargs):
        kwargs['timeout'] = DEFAULT_TIMEOUT
        return super().send(request, **kwargs)


# Создаем сессию с таймаутами
session = requests.Session()
session.mount('http://', TimeoutAdapter())
session.mount('https://', TimeoutAdapter())

# ==================== БАЗА ЗНАНИЙ ====================

# Краткая документация по проекту для системного промпта
PROJECT_KNOWLEDGE = """
Ты - интеллектуальный помощник в системе управления добычей RoboWell Control System (RWCS).

Система состоит из трех основных модулей:

1. СКВАЖИНЫ (Wells) - модель Well
   - Поля: name, depth (м), diameter (мм), pump_depth (м), dynamic_level (м), 
     static_level (м), formation_debit (м³/сут)
   - Эндпоинты: /api/wells/ (список), /api/wells/{id}/ (детали),
     /api/wells/{id}/telemetry/ (телеметрия), /api/wells/statistics/ (статистика)

2. НАСОСЫ ЭЦН (Pumps) - модель PumpCharacteristic
   - Хранит гидравлические характеристики насосов (Q-H, Q-N, Q-КПД)
   - Поля: harka_stupen (марка), nominal_range (номинальная подача, м³/сут),
     nominal_head (номинальный напор, м), max_efficiency (макс. КПД, %),
     stages_count (кол-во ступеней), left_range/right_range (рабочий диапазон)
   - Эндпоинты: /api/pumps/, /api/pumps/{id}/,
     /api/pumps/{id}/characteristics/ (данные для графиков),
     /api/pumps/{id}/calculate_point/?flow=... (расчет в точке),
     /api/pumps/find_suitable/?required_flow=...&required_head=... (подбор насосов),
     /api/pumps/statistics/ (статистика)

3. ЭЛЕКТРОДВИГАТЕЛИ (Motors) - модель ElectricMotor
   - Хранит параметры испытаний двигателей
   - Поля: model (модель), nominal_power (кВт), nominal_voltage (В),
     nominal_current (А), efficiency (КПД, %), power_factor (cos φ),
     vibration_level (вибрация, мм/с), insulation_resistance (изоляция, МОм)
   - Эндпоинты: /api/motors/, /api/motors/{id}/,
     /api/motors/{id}/technical_analysis/ (технический анализ),
     /api/motors/{id}/compare_with_standard/ (сравнение с ГОСТ),
     /api/motors/find_for_pump/?pump_power=... (подбор двигателя для насоса),
     /api/motors/efficiency_statistics/ (статистика по КПД)

Твои возможности:
1. Работа с API системы (скважины, насосы, двигатели)
2. Ответы на технические вопросы (КПД, мощность, вибрация и т.д.)
3. Поиск информации в интернете (если нужно найти документацию, ГОСТы, характеристики)
4. Объяснение терминов и концепций

Как работать:
- Если вопрос касается данных из системы - используй соответствующую функцию API
- Если нужно найти информацию в интернете - используй web_search
- Если вопрос общий технический - отвечай из своих знаний
- Если не уверен - предложи поискать в интернете
"""


# ==================== КЛАСС АССИСТЕНТА ====================

class RoboWellAssistant:
    """
    ИИ-помощник для работы со скважинами, насосами и двигателями.
    """

    def __init__(self):
        """Инициализация помощника с настройками API"""
        self.last_motor_id = None
        self.last_motor_name = None

        self.client = openai.OpenAI(
            base_url=OPENAI_API_URL,
            api_key=OPENAI_API_KEY,
            timeout=DEFAULT_TIMEOUT  # добавляем таймаут для клиента
        )

        # Определяем доступные инструменты для AI
        self.tools = self._define_tools()

        # История разговора
        self.messages = [
            {
                "role": "system",
                "content": PROJECT_KNOWLEDGE + """
                ТЫ - ЭКСПЕРТ-ПОМОЩНИК. Используй функции для получения данных.

                ПРАВИЛА:
                1. Анализируй вопрос и вызывай нужные функции
                2. Если не хватает данных — спрашивай уточнения
                3. Если спрашивают про "самый мощный", "самый глубокий", "максимальный" - используй statistics эндпоинты
                4. Для сравнения используй сортировку (ordering параметр)
                5. Не выдумывай параметры - используй реальные данные из API

                Доступные эндпоинты:
                - /api/pumps/statistics/ - статистика (min, max, avg)
                - /api/pumps/?ordering=-max_efficiency - сортировка по КПД
                - /api/pumps/?ordering=-nominal_range - сортировка по подаче
                - /api/pumps/?ordering=-nominal_head - сортировка по напору

                Для вопроса "самый мощный насос":
                1. Сначала вызови get_pump_statistics() чтобы увидеть максимальные значения
                2. Потом можешь вызвать get_pumps() с сортировкой для деталей
                
                ВАЖНО:
                - ID скважины (well_id) - это число, обычно небольшое (1, 2, 3...)
                - Модель двигателя (например, "ЭДБС250-117") содержит технические индексы, но это НЕ ID скважины
                - Для подбора оборудования к конкретному двигателю нужно:
                  1. Сначала узнать мощность двигателя (уже есть в ответе)
                  2. Потом найти скважину с подходящими параметрами (глубина, дебит)
                  3. Использовать find_equipment_for_well ТОЛЬКО с реальным ID скважины

                Отвечай кратко, по делу, используй реальные данные.
                """
            }
        ]

    def _define_tools(self) -> List[Dict]:
        """Определение всех доступных инструментов"""
        return [
            # ===== ИНСТРУМЕНТЫ ДЛЯ СКВАЖИН =====
            {
                "type": "function",
                "function": {
                    "name": "get_wells",
                    "description": "Получить список всех скважин",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_well_detail",
                    "description": "Получить детальную информацию по скважине",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "well_id": {
                                "type": "integer",
                                "description": "ID скважины"
                            }
                        },
                        "required": ["well_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_well_statistics",
                    "description": "Получить статистику по всем скважинам",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },

            # ===== ИНСТРУМЕНТЫ ДЛЯ НАСОСОВ =====
            {
                "type": "function",
                "function": {
                    "name": "find_pumps",
                    "description": "Поиск подходящих насосов ЭЦН по параметрам",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "required_flow": {
                                "type": "number",
                                "description": "Требуемая подача, м³/сут"
                            },
                            "required_head": {
                                "type": "number",
                                "description": "Требуемый напор, м"
                            },
                            "min_efficiency": {
                                "type": "number",
                                "description": "Минимальный КПД, % (по умолчанию 25)"
                            }
                        },
                        "required": ["required_flow", "required_head"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pump_characteristics",
                    "description": "Получить полные характеристики насоса (для графиков)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pump_id": {
                                "type": "integer",
                                "description": "ID насоса"
                            }
                        },
                        "required": ["pump_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_pump_point",
                    "description": "Рассчитать параметры насоса в заданной точке подачи",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pump_id": {
                                "type": "integer",
                                "description": "ID насоса"
                            },
                            "flow": {
                                "type": "number",
                                "description": "Подача, м³/сут"
                            },
                            "density": {
                                "type": "number",
                                "description": "Плотность жидкости, кг/м³ (по умолчанию 850)"
                            }
                        },
                        "required": ["pump_id", "flow"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pump_statistics",
                    "description": "Получить статистику по всем насосам",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },

            # ===== ИНСТРУМЕНТЫ ДЛЯ ДВИГАТЕЛЕЙ =====
            {
                "type": "function",
                "function": {
                    "name": "find_motors_for_pump",
                    "description": "Подобрать двигатели для насоса по его мощности",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pump_power": {
                                "type": "number",
                                "description": "Мощность насоса, кВт (обязательный параметр)"
                            },
                            "voltage": {
                                "type": "number",
                                "description": "Требуемое напряжение, В (опционально)"
                            },
                            "service_factor": {
                                "type": "number",
                                "description": "Коэффициент запаса (по умолчанию 1.15)"
                            },
                            "min_efficiency": {
                                "type": "number",
                                "description": "Минимальный КПД, % (по умолчанию 80)"
                            }
                        },
                        "required": ["pump_power"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_motor_technical_analysis",
                    "description": "Получить технический анализ двигателя",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "motor_id": {
                                "type": "integer",
                                "description": "ID двигателя"
                            }
                        },
                        "required": ["motor_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_motor_efficiency_statistics",
                    "description": "Получить статистику по КПД двигателей",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },

            # ===== ИНСТРУМЕНТЫ ДЛЯ ПОИСКА В ИНТЕРНЕТЕ =====
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Выполнить поиск в интернете по любому вопросу (технические характеристики, термины, документация, ГОСТы и т.д.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос (что нужно найти)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },

            # ===== КОМБИНИРОВАННЫЕ ИНСТРУМЕНТЫ =====
            {
                "type": "function",
                "function": {
                    "name": "find_equipment_for_well",
                    "description": "Подобрать насос и двигатель для скважины по ее параметрам",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "well_id": {
                                "type": "integer",
                                "description": "ID скважины"
                            }
                        },
                        "required": ["well_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pump_power_by_model",
                    "description": "Получить мощность насоса по его модели/марке",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pump_model": {
                                "type": "string",
                                "description": "Модель или марка насоса (например, 'ТД1750-200')"
                            }
                        },
                        "required": ["pump_model"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_equipment_by_well_name",
                    "description": "Подобрать насос и двигатель для скважины по ее имени (например, 'Скважина №11022')",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "well_name": {
                                "type": "string",
                                "description": "Имя скважины (поле name)"
                            }
                        },
                        "required": ["well_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_pumps",
                    "description": "Получить список насосов с возможностью сортировки. Для сортировки используй: '-nominal_range' (по мощности), '-max_efficiency' (по КПД), '-nominal_head' (по напору)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ordering": {
                                "type": "string",
                                "description": "Поле для сортировки (например, '-nominal_range' для самых мощных)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Сколько показать (по умолчанию 5)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_motors",
                    "description": "Получить список двигателей с возможностью сортировки. Для сортировки используй: '-nominal_power' (по мощности), '-efficiency' (по КПД)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ordering": {
                                "type": "string",
                                "description": "Поле для сортировки (например, '-nominal_power' для самых мощных)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Сколько показать (по умолчанию 5)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_wells",
                    "description": "Получить список скважин с возможностью сортировки. Для сортировки используй: '-depth' (по глубине), '-formation_debit' (по дебиту)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ordering": {
                                "type": "string",
                                "description": "Поле для сортировки (например, '-depth' для самых глубоких)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Сколько показать (по умолчанию 5)"
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

    # ==================== МЕТОДЫ ДЛЯ СКВАЖИН ====================

    def get_wells(self) -> str:
        """Получить список всех скважин"""
        print("\n🔍 Получение списка скважин...")
        try:
            url = f"{API_BASE_URL}/wells/"
            print(f"   Запрос: {url}")
            response = session.get(url, timeout=DEFAULT_TIMEOUT)
            print(f"   Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Тип данных: {type(data)}")

                # Проверяем, что данные - это список
                if isinstance(data, list):
                    wells = data
                    print(f"   Получено скважин: {len(wells)}")
                elif isinstance(data, dict) and 'results' in data:
                    # Если используется пагинация
                    wells = data['results']
                    print(f"   Получено скважин (с пагинацией): {len(wells)}")
                else:
                    wells = []
                    print(f"   Неожиданный формат данных: {data}")

                if not wells:
                    return "❌ В базе данных нет скважин. Добавьте скважины через админку или API."

                # Безопасно берем первые 5
                result = f"✅ Найдено {len(wells)} скважин:\n\n"
                for i, well in enumerate(wells):
                    if i >= 5:  # Показываем только первые 5
                        break

                    # Безопасно получаем значения
                    name = well.get('name', 'Без имени') if isinstance(well, dict) else 'Некорректные данные'
                    depth = well.get('depth', 'Н/Д') if isinstance(well, dict) else 'Н/Д'
                    debit = well.get('formation_debit', 'Н/Д') if isinstance(well, dict) else 'Н/Д'

                    result += f"• {name}\n"
                    result += f"  Глубина: {depth}\n"
                    result += f"  Дебит: {debit}\n\n"

                if len(wells) > 5:
                    result += f"... и еще {len(wells) - 5} скважин"

                return result
            else:
                print(f"   Ошибка ответа: {response.text[:200]}")
                return f"❌ Ошибка при получении скважин: {response.status_code}"

        except requests.exceptions.Timeout:
            return "❌ Таймаут при запросе к API скважин"
        except Exception as e:
            print(f"   Исключение: {str(e)}")
            import traceback
            traceback.print_exc()  # Печатаем полный стек ошибки
            return f"❌ Ошибка: {str(e)}"

    def find_equipment_by_well_name(self, well_name: str) -> str:
        """
        Подобрать насос и двигатель для скважины по ее имени
        """
        print(f"\n🔍 Подбор оборудования для скважины с именем: {well_name}")

        try:
            # Получаем все скважины
            url = f"{API_BASE_URL}/wells/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code != 200:
                return f"❌ Ошибка при поиске скважины: {response.status_code}"

            data = response.json()

            # Получаем список скважин
            if isinstance(data, dict) and 'results' in data:
                wells = data['results']
            elif isinstance(data, list):
                wells = data
            else:
                wells = []

            if not wells:
                return f"❌ В базе данных нет скважин."

            # Показываем все доступные скважины для отладки
            print("📋 Доступные скважины в БД:")
            for w in wells:
                print(f"   - '{w.get('name')}' (ID: {w.get('id')})")

            # Ищем скважину
            target_well = None

            # Очищаем поисковый запрос от лишних символов
            search_term = well_name.strip()

            for well in wells:
                db_name = well.get('name', '')

                # Проверяем различные варианты совпадения
                if (db_name == search_term or  # точное совпадение
                        search_term in db_name or  # поиск в имени БД
                        db_name in search_term or  # имя БД в поиске
                        # Поиск по номеру скважины (цифры)
                        any(num in db_name for num in re.findall(r'\d+', search_term))):
                    target_well = well
                    print(f"   ✅ Найдено совпадение: '{db_name}'")
                    break

            if not target_well:
                # Если не нашли, показываем все скважины пользователю
                well_list = "\n".join([f"   • {w.get('name')}" for w in wells])
                return f"""❌ Скважина "{well_name}" не найдена.

    📋 Доступные скважины в системе:
    {well_list}

    💡 Подсказка: Используйте точное название скважины из списка выше, например:
       "Подбери оборудование для Куст №10, скважина №265 Коттынское месторождение"
    """

            well_id = target_well.get('id')
            if not well_id:
                return f"❌ Не удалось определить ID скважины"

            # Вызываем подбор оборудования
            return self.find_equipment_for_well(well_id)

        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_wells_data(self) -> list:
        """Получить сырые данные скважин (не форматированный текст)"""
        try:
            url = f"{API_BASE_URL}/wells/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'results' in data:
                    wells = data['results']
                elif isinstance(data, list):
                    wells = data
                else:
                    wells = []

                print(f"   Получено {len(wells)} скважин")
                for well in wells:
                    print(f"   Well {well.get('id')}: name={well.get('name')}, debit='{well.get('formation_debit')}'")
                return wells
            return []
        except Exception as e:
            print(f"   Ошибка получения данных скважин: {e}")
            return []

    def get_well_detail(self, well_id: int) -> str:
        """Получить детальную информацию по скважине"""
        print(f"\n🔍 Получение деталей скважины {well_id}...")
        try:
            url = f"{API_BASE_URL}/wells/{well_id}/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                well = response.json()
                return f"""
✅ Скважина: {well.get('name')}
   • Глубина: {well.get('depth')}
   • Диаметр колонны: {well.get('diameter')}
   • Глубина спуска насоса: {well.get('pump_depth')}
   • Динамический уровень: {well.get('dynamic_level')}
   • Статический уровень: {well.get('static_level')}
   • Пластовый дебит: {well.get('formation_debit')}
   • Создана: {well.get('created_at')}
"""
            else:
                return f"❌ Скважина с ID {well_id} не найдена"
        except requests.exceptions.Timeout:
            return f"❌ Таймаут при запросе скважины {well_id}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_well_statistics(self) -> str:
        """Получить статистику по всем скважинам"""
        print("\n🔍 Получение статистики по скважинам...")
        try:
            url = f"{API_BASE_URL}/wells/statistics/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                stats = response.json()
                return f"""
📊 СТАТИСТИКА ПО СКВАЖИНАМ:
   • Всего скважин: {stats.get('total_wells')}
   • Средняя глубина: {stats.get('avg_depth'):.1f} м
   • Макс. глубина: {stats.get('max_depth'):.1f} м
   • Мин. глубина: {stats.get('min_depth'):.1f} м
   • Суммарный дебит: {stats.get('total_debit'):.1f} м³/сут
"""
            else:
                return f"❌ Ошибка: {response.status_code}"
        except requests.exceptions.Timeout:
            return "❌ Таймаут при получении статистики"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    # ==================== МЕТОДЫ ДЛЯ НАСОСОВ ====================

    def find_pumps(self, required_flow: float, required_head: float, min_efficiency: float = 25) -> str:
        """Поиск подходящих насосов"""
        print(f"\n🔍 Поиск насосов: Q={required_flow}, H={required_head}, КПД>={min_efficiency}")
        try:
            url = f"{API_BASE_URL}/pumps/find_suitable/"
            params = {
                "required_flow": required_flow,
                "required_head": required_head,
                "min_efficiency": min_efficiency
            }
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                pumps = data.get('pumps', [])

                if not pumps:
                    return f"❌ Насосов с Q={required_flow}, H={required_head} не найдено."

                result = f"✅ Найдено {data['found_count']} насосов. Топ-3:\n\n"
                for i, pump in enumerate(pumps[:3], 1):
                    result += f"{i}. **{pump['harka_stupen']}**\n"
                    result += f"   📊 Qном: {pump.get('nominal_range')} м³/сут\n"
                    result += f"   📈 H: {pump.get('nominal_head_display')}\n"
                    result += f"   ⚡ КПД в точке: {pump.get('calculated_efficiency', 0):.1f}%\n"
                    result += f"   🔧 Производитель: {pump.get('zavod')}\n\n"
                return result
            else:
                return f"❌ Ошибка API: {response.status_code}"
        except requests.exceptions.Timeout:
            return "❌ Таймаут при поиске насосов"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_pump_characteristics(self, pump_id: int) -> str:
        """Получить характеристики насоса для графиков"""
        print(f"\n🔍 Получение характеристик насоса {pump_id}...")
        try:
            url = f"{API_BASE_URL}/pumps/{pump_id}/characteristics/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                pump = data.get('pump_info', {})
                chars = data.get('characteristics', {})

                result = f"""
📊 ХАРАКТЕРИСТИКИ НАСОСА {pump.get('name')}:
   • Производитель: {pump.get('manufacturer')}
   • Qном: {pump.get('nominal_flow')} м³/сут
   • Hном: {pump.get('nominal_head')} м
   • Ступеней: {pump.get('stages')}

   Данные для построения графиков:
   • Q (подача): {chars.get('q_values', [])[:5]}...
   • H (напор): {chars.get('h_values', [])[:5]}...
   • N (мощность): {chars.get('n_values', [])[:5]}...
   • КПД: {chars.get('kpd_values', [])[:5]}...
"""
                return result
            else:
                return f"❌ Насос {pump_id} не найден"
        except requests.exceptions.Timeout:
            return f"❌ Таймаут при получении характеристик насоса {pump_id}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def calculate_pump_point(self, pump_id: int, flow: float, density: float = 850) -> str:
        """Рассчитать параметры насоса в точке"""
        print(f"\n🔍 Расчет насоса {pump_id} при Q={flow}, ρ={density}...")
        try:
            url = f"{API_BASE_URL}/pumps/{pump_id}/calculate_point/"
            params = {"flow": flow, "density": density}
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                chars = data.get('characteristics', {})
                power = data.get('power_calculation', {})
                reco = data.get('recommendation', {})

                result = f"""
📊 РАСЧЕТ НАСОСА ID={pump_id} ПРИ Q={flow} м³/сут:
   • Напор: {chars.get('h', 0):.1f} м
   • Мощность на валу: {chars.get('n', 0):.1f} кВт
   • КПД: {chars.get('kpd', 0):.1f}%

   • Гидравлическая мощность: {power.get('hydraulic_power_kw', 0):.1f} кВт
   • Потребляемая мощность: {power.get('shaft_power_kw', 0):.1f} кВт

   РЕКОМЕНДАЦИЯ: {reco.get('status')} - {', '.join(reco.get('messages', []))}
"""
                return result
            else:
                return f"❌ Ошибка расчета: {response.status_code}"
        except requests.exceptions.Timeout:
            return f"❌ Таймаут при расчете насоса {pump_id}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_pump_statistics(self) -> str:
        """Получить статистику по всем насосам"""
        print("\n🔍 Получение статистики по насосам...")
        try:
            url = f"{API_BASE_URL}/pumps/statistics/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                stats = response.json()
                return f"""
📊 СТАТИСТИКА ПО НАСОСАМ:
   • Всего насосов: {stats.get('total_pumps')}
   • Производители: {', '.join(map(str, stats.get('manufacturers', [])))}

   Диапазон подач:
   • Мин: {stats.get('flow_range', {}).get('min')} м³/сут
   • Макс: {stats.get('flow_range', {}).get('max')} м³/сут
   • Средняя: {stats.get('flow_range', {}).get('avg'):.1f} м³/сут

   Диапазон КПД:
   • Мин: {stats.get('efficiency_range', {}).get('min')}%
   • Макс: {stats.get('efficiency_range', {}).get('max')}%
   • Средний: {stats.get('efficiency_range', {}).get('avg'):.1f}%
"""
            else:
                return f"❌ Ошибка: {response.status_code}"
        except requests.exceptions.Timeout:
            return "❌ Таймаут при получении статистики насосов"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    # ==================== МЕТОДЫ ДЛЯ ДВИГАТЕЛЕЙ ====================

    def find_motors_for_pump(self, pump_power: float, voltage: Optional[float] = None,
                             service_factor: float = 1.15, min_efficiency: float = 80) -> str:
        """Подобрать двигатели для насоса через API /motors/find_for_pump/"""
        print(f"\n🔍 Подбор двигателей для насоса мощностью {pump_power} кВт...")

        try:
            url = f"{API_BASE_URL}/motors/find_for_pump/"
            params = {
                "pump_power": pump_power,
                "service_factor": service_factor,
                "min_efficiency": min_efficiency
            }
            if voltage:
                params["voltage"] = voltage

            print(f"   Запрос: {url} с параметрами {params}")
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            print(f"   Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                motors = data.get('motors', [])

                if not motors:
                    return f"❌ Двигателей для насоса {pump_power} кВт не найдено."

                # Сохраняем первый двигатель для последующих вопросов
                if len(motors) > 0:
                    self.last_motor_id = motors[0].get('id')
                    self.last_motor_name = motors[0].get('model')
                    print(f"   💾 Запомнил двигатель: {self.last_motor_name} (ID: {self.last_motor_id})")

                result = f"✅ Найдено {data.get('found_count', len(motors))} двигателей для насоса мощностью {pump_power:.2f} кВт:\n\n"

                for i, motor in enumerate(motors[:3], 1):
                    result += f"{i}. **{motor.get('model', 'Неизвестно')}**\n"
                    result += f"   ⚡ Мощность: {motor.get('nominal_power', '?')} кВт\n"
                    result += f"   🔌 Напряжение: {motor.get('nominal_voltage', '?')} В\n"
                    result += f"   📈 КПД: {motor.get('efficiency', '?')}%\n"

                    if 'power_match_percentage' in motor:
                        result += f"   📊 Запас мощности: {motor['power_match_percentage']:.1f}%\n"
                    result += "\n"

                # ВАЖНО: Просто возвращаем результат, не отправляем в AI
                return result
            else:
                try:
                    error_data = response.json()
                    return f"❌ Ошибка API: {error_data}"
                except:
                    return f"❌ Ошибка API: статус {response.status_code}"

        except requests.exceptions.Timeout:
            return "❌ Таймаут при подборе двигателей"
        except requests.exceptions.ConnectionError:
            return "❌ Ошибка подключения: Django сервер не запущен"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_motor_efficiency_statistics(self) -> str:
        """Получить статистику по КПД двигателей"""
        print("\n🔍 Получение статистики по КПД двигателей...")
        try:
            url = f"{API_BASE_URL}/motors/efficiency_statistics/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                stats = response.json()
                return f"""
📊 СТАТИСТИКА ПО ДВИГАТЕЛЯМ:
   • Всего двигателей: {stats.get('total_motors')}
   • Производители: {', '.join(map(str, stats.get('manufacturers', [])))}

   КПД:
   • Мин: {stats.get('efficiency', {}).get('min')}%
   • Макс: {stats.get('efficiency', {}).get('max')}%
   • Средний: {stats.get('efficiency', {}).get('avg'):.1f}%

   Распределение по классам:
   • IE3 (≥90%): {stats.get('efficiency_classes', {}).get('IE3')}
   • IE2 (85-89%): {stats.get('efficiency_classes', {}).get('IE2')}
   • IE1 (80-84%): {stats.get('efficiency_classes', {}).get('IE1')}
   • Ниже стандарта: {stats.get('efficiency_classes', {}).get('below')}
"""
            else:
                return f"❌ Ошибка: {response.status_code}"
        except requests.exceptions.Timeout:
            return "❌ Таймаут при получении статистики двигателей"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    def get_motor_technical_analysis(self, motor_id: int) -> str:
        """
        Получить технический анализ двигателя по ID
        """
        print(f"\n🔍 Технический анализ двигателя ID={motor_id}...")

        try:
            url = f"{API_BASE_URL}/motors/{motor_id}/technical_analysis/"
            response = session.get(url, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                motor_info = data.get('motor_info', {})
                calculations = data.get('calculations', {})
                assessments = data.get('assessments', {})
                recommendations = data.get('recommendations', [])

                result = f"""
📊 ТЕХНИЧЕСКИЙ АНАЛИЗ ДВИГАТЕЛЯ {motor_info.get('model')}:

🔧 ОСНОВНЫЕ ПАРАМЕТРЫ:
  • Мощность: {motor_info.get('nominal_power')} кВт
  • Напряжение: {motor_info.get('nominal_voltage')} В

📈 РАСЧЕТЫ:
  • Момент на валу: {calculations.get('rated_torque_nm', 0):.1f} Нм
  • Кратность пускового тока: {calculations.get('starting_current_ratio', 0):.1f}
  • Потребление энергии: {calculations.get('power_consumption', {}).get('daily_consumption_kwh', 0):.0f} кВт·ч/сутки

🔍 ОЦЕНКИ:
  • Вибрация: {assessments.get('vibration', {}).get('status')} ({assessments.get('vibration', {}).get('level')} мм/с)
  • Класс энергоэффективности: {assessments.get('efficiency_class')}

💡 РЕКОМЕНДАЦИИ:
"""
                for rec in recommendations:
                    result += f"  • {rec.get('message')}\n"

                return result
            else:
                return f"❌ Двигатель с ID {motor_id} не найден"

        except requests.exceptions.Timeout:
            return f"❌ Таймаут при анализе двигателя {motor_id}"
        except requests.exceptions.ConnectionError:
            return "❌ Ошибка подключения: Django сервер не запущен"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    # ==================== МЕТОДЫ ДЛЯ ПОИСКА В ИНТЕРНЕТЕ ====================

    def web_search(self, query: str) -> str:
        """
        Выполнить поиск в интернете по любому запросу
        """
        print(f"\n🔍 Поиск в интернете: {query}")

        try:
            # Используем публичное API DuckDuckGo (без ключа)
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }

            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code == 200:
                data = response.json()

                # Основное описание
                abstract = data.get('Abstract', '')
                if abstract:
                    return f"📚 {abstract}"

                # Если нет Abstract, берем связанные темы
                topics = data.get('RelatedTopics', [])
                if topics:
                    result = "📚 Результаты поиска:\n"
                    count = 0
                    for topic in topics:
                        if isinstance(topic, dict) and 'Text' in topic:
                            result += f"• {topic['Text'][:200]}...\n"
                            count += 1
                            if count >= 5:
                                break
                    return result

                return "❌ Ничего не найдено по запросу"
            else:
                return f"❌ Ошибка поиска: {response.status_code}"

        except requests.exceptions.Timeout:
            return "❌ Таймаут при поиске в интернете"
        except Exception as e:
            return f"❌ Ошибка при поиске: {str(e)}"

    # ==================== МЕТОДЫ ДЛЯ НАСОСОВ (НОВЫЕ) ====================

    def get_pump_power_by_model(self, pump_model: str) -> str:
        """
        Получить мощность насоса по его модели/марке
        """
        print(f"\n🔍 Поиск мощности насоса по модели: {pump_model}")

        try:
            url = f"{API_BASE_URL}/pumps/"
            params = {"search": pump_model}

            print(f"   Запрос: {url} с параметрами {params}")
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if response.status_code != 200:
                return f"❌ Ошибка при поиске насоса: {response.status_code}"

            data = response.json()

            # Обработка ответа
            if isinstance(data, dict) and 'results' in data:
                pumps = data['results']
            elif isinstance(data, list):
                pumps = data
            else:
                pumps = []

            if not pumps:
                return f"❌ Насос с моделью '{pump_model}' не найден."

            pump = pumps[0]
            pump_id = pump.get('id')
            nominal_range = pump.get('nominal_range')

            if not pump_id or not nominal_range:
                return f"❌ Не удалось определить параметры насоса"

            calc_url = f"{API_BASE_URL}/pumps/{pump_id}/calculate_point/"
            calc_params = {"flow": nominal_range}

            calc_response = session.get(calc_url, params=calc_params, timeout=DEFAULT_TIMEOUT)

            if calc_response.status_code == 200:
                calc_data = calc_response.json()
                power = calc_data.get('characteristics', {}).get('n', 0)

                if power and power > 0:
                    print(f"   Получена мощность: {power} кВт")

                    motor_result = self.find_motors_for_pump(
                        pump_power=float(power),
                        service_factor=1.15,
                        min_efficiency=80
                    )

                    # ВОЗВРАЩАЕМ ТОЛЬКО РЕЗУЛЬТАТ, НЕ ДОБАВЛЯЕМ В ИСТОРИЮ
                    return f"✅ Насос {pump_model} имеет мощность {power:.2f} кВт.\n\n{motor_result}"

            return f"❌ Не удалось рассчитать мощность для насоса {pump_model}"

        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

        def select_equipment_via_api(self, well_id: int) -> str:
            """НОВЫЙ МЕТОД: подбор оборудования через прямой вызов API"""
            import requests

            print(f"\n🚀 НОВЫЙ МЕТОД: select_equipment_via_api для скважины {well_id}")

            try:
                url = f"{API_BASE_URL}/pumps/select_for_well/"
                response = requests.get(url, params={"well_id": well_id, "service_factor": 1.15}, timeout=10)

                print(f"   Статус: {response.status_code}")

                if response.status_code != 200:
                    return f"❌ Ошибка API: {response.status_code}"

                data = response.json()
                found = data.get('found_count', 0)
                recs = data.get('recommendations', [])

                if found == 0:
                    return "❌ Подходящие насосы не найдены"

                result = f"✅ НАЙДЕНО {found} ВАРИАНТОВ ПОДБОРА:\n\n"

                for i, rec in enumerate(recs[:5], 1):
                    pump = rec.get('pump', {})
                    motor = rec.get('motor', {})
                    point = rec.get('pump_at_point', {})

                    result += f"{i}. 🌀 {pump.get('name', '?')}\n"
                    result += f"   • Подача: {point.get('flow', 0):.0f} м³/сут\n"
                    result += f"   • Напор: {point.get('head', 0):.0f} м\n"
                    result += f"   • КПД насоса: {point.get('efficiency', 0):.1f}%\n"
                    result += f"   • Двигатель: {motor.get('model', '?')}\n"
                    result += f"   • Мощность двигателя: {motor.get('power', 0)} кВт\n"
                    result += f"   • КПД двигателя: {motor.get('efficiency', 0):.1f}%\n\n"

                return result

            except Exception as e:
                return f"❌ Ошибка: {str(e)}"

    # ==================== КОМБИНИРОВАННЫЕ МЕТОДЫ ====================

    def find_equipment_for_well(self, well_id: int) -> str:
        """Подобрать насос и двигатель для скважины (используя API)"""
        print(f"\n🔧 Подбор оборудования для скважины ID={well_id}...")

        try:
            # Используем API эндпоинт, который уже работает
            url = f"{API_BASE_URL}/pumps/select_for_well/"
            params = {
                "well_id": well_id,
                "service_factor": 1.15
            }

            print(f"   Запрос: {url} с params={params}")
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            print(f"   Статус ответа: {response.status_code}")

            if response.status_code != 200:
                return f"❌ Ошибка при подборе оборудования: {response.status_code}"

            data = response.json()

            well_info = data.get('well', {})
            params_info = data.get('selection_parameters', {})
            recommendations = data.get('recommendations', [])
            found_count = data.get('found_count', 0)

            # Формируем ответ
            result = f"""
    🔍 ПОДБОР ОБОРУДОВАНИЯ ДЛЯ СКВАЖИНЫ {well_info.get('name')} (ID={well_id}):

    📊 ПАРАМЕТРЫ СКВАЖИНЫ:
       • Глубина: {well_info.get('depth', '?')} м
       • Пластовое давление: {well_info.get('reservoir_pressure', '?')} МПа
       • Коэффициент продуктивности: {well_info.get('productivity_index', '?')} м³/сут·МПа
       • Обводненность: {well_info.get('water_cut', '?')}%

    📐 РАСЧЕТНЫЕ ПАРАМЕТРЫ:
       • Целевой дебит: {params_info.get('target_flow', '?'):.1f} м³/сут
       • Потребный напор: {params_info.get('required_head', '?'):.0f} м
       • Газосодержание на приеме: {params_info.get('gas_fraction', '?'):.1f}%
       • Глубина спуска насоса: {well_info.get('pump_depth', '?'):.0f} м

    """

            if found_count == 0:
                result += """
    ❌ ПОДХОДЯЩИЕ НАСОСЫ НЕ НАЙДЕНЫ

    Рекомендации:
       • Увеличьте целевой дебит
       • Рассмотрите возможность использования насоса с большим количеством ступеней
    """
            else:
                result += f"✅ НАЙДЕНО {found_count} ВАРИАНТОВ (показаны первые 5):\n\n"

                for i, rec in enumerate(recommendations[:5], 1):
                    pump = rec.get('pump', {})
                    motor = rec.get('motor', {})
                    pump_point = rec.get('pump_at_point', {})

                    pump_eff = pump_point.get('efficiency', 0)
                    motor_eff = motor.get('efficiency', 0)
                    overall = rec.get('overall_efficiency', 0)

                    # Оценка эффективности
                    if pump_eff >= 50:
                        eff_rating = "🟢 Хорошо"
                    elif pump_eff >= 35:
                        eff_rating = "🟡 Удовлетворительно"
                    else:
                        eff_rating = "🔴 Низкая эффективность"

                    result += f"{i}. **Насос: {pump.get('name', '?')}**\n"
                    result += f"   • Рабочий диапазон: {pump.get('working_range', ['?', '?'])[0]} - {pump.get('working_range', ['?', '?'])[1]} м³/сут\n"
                    result += f"   • В рабочей точке: Q={pump_point.get('flow', '?'):.0f} м³/сут, H={pump_point.get('head', '?'):.0f} м\n"
                    result += f"   • КПД насоса: {pump_eff:.1f}% ({eff_rating})\n"
                    result += f"   • Мощность на валу: {pump_point.get('power', '?'):.1f} кВт\n"
                    result += f"   • Двигатель: {motor.get('model', '?')} ({motor.get('power', '?')} кВт)\n"
                    if motor_eff > 0:
                        result += f"   • КПД двигателя: {motor_eff:.1f}%\n"
                    result += f"   • Общий КПД системы: {overall:.1f}%\n\n"

                # Добавляем рекомендации по улучшению
                result += """
    💡 РЕКОМЕНДАЦИИ:
       • Для улучшения КПД рассмотрите насос с номинальной подачей ближе к 80 м³/сут
       • Текущий КПД низкий из-за работы насоса на левой границе диапазона
       • Рекомендуется увеличить дебит скважины до 150-200 м³/сут для оптимальной работы
    """

            return result

        except Exception as e:
            print(f"   Ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"❌ Ошибка при подборе оборудования: {str(e)}"

    def select_equipment_via_api(self, well_id: int) -> str:
        """НОВЫЙ МЕТОД: подбор оборудования через прямой вызов API"""
        import requests

        print(f"\n🚀 НОВЫЙ МЕТОД: select_equipment_via_api для скважины {well_id}")

        try:
            url = f"{API_BASE_URL}/pumps/select_for_well/"
            response = requests.get(url, params={"well_id": well_id, "service_factor": 1.15}, timeout=10)

            print(f"   Статус: {response.status_code}")

            if response.status_code != 200:
                return f"❌ Ошибка API: {response.status_code}"

            data = response.json()
            found = data.get('found_count', 0)
            recs = data.get('recommendations', [])

            if found == 0:
                return "❌ Подходящие насосы не найдены"

            result = f"✅ НАЙДЕНО {found} ВАРИАНТОВ ПОДБОРА:\n\n"

            for i, rec in enumerate(recs[:5], 1):
                pump = rec.get('pump', {})
                motor = rec.get('motor', {})
                point = rec.get('pump_at_point', {})

                result += f"{i}. 🌀 {pump.get('name', '?')}\n"
                result += f"   • Подача: {point.get('flow', 0):.0f} м³/сут\n"
                result += f"   • Напор: {point.get('head', 0):.0f} м\n"
                result += f"   • КПД насоса: {point.get('efficiency', 0):.1f}%\n"
                result += f"   • Двигатель: {motor.get('model', '?')}\n"
                result += f"   • Мощность двигателя: {motor.get('power', 0)} кВт\n"
                result += f"   • КПД двигателя: {motor.get('efficiency', 0):.1f}%\n\n"

            return result

        except Exception as e:
            return f"❌ Ошибка: {str(e)}"



    # ==================== ОСНОВНОЙ МЕТОД ====================

    def ask(self, user_question: str) -> str:
        """
        Задать вопрос ассистенту. AI сам решает, какие функции вызывать.
        """
        # ОТЛАДКА
        print("\n" + "=" * 60)
        print(f"📝 ask() получил вопрос: {user_question}")
        print("=" * 60)

        # ПРЯМАЯ ОБРАБОТКА ПОДБОРА ОБОРУДОВАНИЯ
        if "подбер" in user_question.lower() and "оборудован" in user_question.lower():
            print("🔧 ВОШЛИ В ПРЯМУЮ ОБРАБОТКУ ПОДБОРА")

            import re
            # Ищем ID скважины
            match = re.search(r'скважин[ыe]\s*(\d+)', user_question.lower())
            if not match:
                match = re.search(r'ID\s*(\d+)', user_question.lower())

            if match:
                well_id = int(match.group(1))
                print(f"🎯 Найден ID скважины: {well_id}")
                # result = self.find_equipment_for_well(well_id)
                result = self.select_equipment_via_api(well_id)
                self.messages.append({"role": "assistant", "content": result})
                return result
            else:
                print("⚠️ ID скважины не найден, показываем список")
                result = self.get_wells()
                self.messages.append({"role": "assistant", "content": result})
                return result

        # Если вопрос не про двигатели, сбрасываем last_motor_id
        if "двигател" not in user_question.lower() and "мотор" not in user_question.lower():
            if self.last_motor_id:
                print(f"   🧹 Сброс контекста двигателя (был ID={self.last_motor_id})")
                self.last_motor_id = None
                self.last_motor_name = None

        # Ограничиваем историю сообщений (оставляем последние 10)
        if len(self.messages) > 10:
            # Всегда сохраняем первое системное сообщение
            system_msg = self.messages[0]
            # Берем последние 9 сообщений
            self.messages = [system_msg] + self.messages[-9:]
            print(f"   📋 История сокращена до {len(self.messages)} сообщений")

        print(f"\n📝 Обработка вопроса: {user_question}")

        # Добавляем вопрос пользователя
        self.messages.append({"role": "user", "content": user_question})

        # Если есть последний двигатель, добавляем подсказку в контекст
        if self.last_motor_id:
            context_hint = f"(Последний обсуждаемый двигатель: {self.last_motor_name} с ID={self.last_motor_id})"
            print(f"   Контекст: {context_hint}")
            self.messages.append({"role": "system", "content": context_hint})

        print(f"   Отправляю в AI {len(self.messages)} сообщений...")

        try:
            # Отправляем запрос с возможностью вызова функций
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto",
                timeout=30
            )

            print(f"   Получил ответ от AI")

            message = response.choices[0].message

            # ===== ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА ДЛЯ ПОДБОРА ОБОРУДОВАНИЯ =====
            # Проверяем, не пытается ли AI просто описать действия вместо вызова функции
            # ===== ПРЯМОЙ ВЫЗОВ НОВОГО МЕТОДА =====
            if "подбер" in user_question.lower() and "скважин" in user_question.lower():
                print("   🚀 ПРЯМОЙ ВЫЗОВ НОВОГО МЕТОДА")

                import re
                match = re.search(r'(\d+)', user_question)
                if match:
                    well_id = int(match.group(1))
                    print(f"   🎯 ID скважины: {well_id}")
                    result = self.select_equipment_via_api(well_id)
                    self.messages.append({"role": "assistant", "content": result})
                    return result
                else:
                    # Если ID не найден, показываем список скважин
                    return self.get_wells()

            # Проверяем, хочет ли AI вызвать функцию
            if message.tool_calls:
                print(f"\n🤖 Ассистент вызывает функцию: {message.tool_calls[0].function.name}")

                # Сохраняем сообщение с вызовом функции
                self.messages.append(message)

                # Обрабатываем каждый вызов функции
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    print(f"   Аргументы: {args}")

                    # Вызываем соответствующую функцию
                    function_result = self._call_function(function_name, args)

                    # Отправляем результат обратно
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_result
                    })

                # Получаем финальный ответ от AI
                second_response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.messages,
                    timeout=30
                )
                final_answer = second_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_answer})

                # Удаляем подсказку после использования
                if len(self.messages) > 1 and self.messages[-2][
                    "role"] == "system" and "Последний обсуждаемый двигатель" in self.messages[-2]["content"]:
                    self.messages.pop(-2)

                return final_answer

            else:
                # Простой ответ без вызова функций
                answer = message.content
                self.messages.append({"role": "assistant", "content": answer})
                return answer

        except Exception as e:
            error_msg = f"❌ Ошибка при обращении к AI: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def _call_function(self, function_name: str, args: Dict) -> str:
        """Вызов функции по имени"""
        functions = {
            # Скважины
            "get_wells": lambda: self.get_wells(
                args.get("ordering"),
                args.get("limit", 5)
            ),
            "get_well_detail": lambda: self.get_well_detail(args.get("well_id")),
            "get_well_statistics": lambda: self.get_well_statistics(),

            # Насосы
            "get_pumps": lambda: self.get_pumps(
                args.get("ordering"),
                args.get("limit", 5)
            ),
            "find_pumps": lambda: self.find_pumps(
                args.get("required_flow"),
                args.get("required_head"),
                args.get("min_efficiency", 25)
            ),
            "get_pump_characteristics": lambda: self.get_pump_characteristics(args.get("pump_id")),
            "calculate_pump_point": lambda: self.calculate_pump_point(
                args.get("pump_id"),
                args.get("flow"),
                args.get("density", 850)
            ),
            "get_pump_statistics": lambda: self.get_pump_statistics(),

            # Двигатели
            "get_motors": lambda: self.get_motors(
                args.get("ordering"),
                args.get("limit", 5)
            ),
            "find_motors_for_pump": lambda: self.find_motors_for_pump(
                args.get("pump_power"),
                args.get("voltage"),
                args.get("service_factor", 1.15),
                args.get("min_efficiency", 80)
            ),
            "get_motor_technical_analysis": lambda: self.get_motor_technical_analysis(args.get("motor_id")),
            "get_motor_efficiency_statistics": lambda: self.get_motor_efficiency_statistics(),

            # Поиск в интернете
            "web_search": lambda: self.web_search(args.get("query")),

            # Комбинированные
            "find_equipment_for_well": lambda: self.find_equipment_for_well(args.get("well_id")),
            "get_pump_power_by_model": lambda: self.get_pump_power_by_model(args.get("pump_model")),
            "find_equipment_by_well_name": lambda: self.find_equipment_by_well_name(args.get("well_name")),
        }

        if function_name in functions:
            try:
                result = functions[function_name]()
                print(f"   ✅ Функция {function_name} выполнена успешно")
                return result
            except Exception as e:
                print(f"   ❌ Ошибка в функции {function_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                return f"❌ Ошибка при выполнении {function_name}: {str(e)}"
        else:
            return f"❌ Неизвестная функция: {function_name}"

    def get_pumps(self, ordering: str = None, limit: int = 5) -> str:
        """Получить список насосов с сортировкой"""
        print(f"\n📢 Вызван get_pumps с ordering={ordering}, limit={limit}")
        result = self._get_items("pumps", ordering, limit,
                                 display_fields=['harka_stupen', 'nominal_range', 'nominal_head_display',
                                                 'max_efficiency_display'])
        print(f"📢 Результат get_pumps: {result[:100]}...")
        return result

    def get_motors(self, ordering: str = None, limit: int = 5) -> str:
        """Получить список двигателей с сортировкой"""
        return self._get_items("motors", ordering, limit,
                               display_fields=['model', 'nominal_power', 'nominal_voltage', 'efficiency'])

    def get_wells(self, ordering: str = None, limit: int = 5) -> str:
        """Получить список скважин с сортировкой"""
        return self._get_items("wells", ordering, limit,
                               display_fields=['name', 'depth', 'formation_debit'])

    def _get_items(self, endpoint: str, ordering: str = None, limit: int = 5, display_fields: list = None) -> str:
        """Универсальный метод получения списка с сортировкой"""
        print(f"\n🔍 Получение списка {endpoint}...")
        try:
            url = f"{API_BASE_URL}/{endpoint}/"
            params = {}
            if ordering:
                params['ordering'] = ordering
                print(f"   Сортировка: {ordering}")

            print(f"   Запрос: {url} с параметрами {params}")
            response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            print(f"   Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   Тип данных: {type(data)}")

                # Извлекаем элементы
                if isinstance(data, dict) and 'results' in data:
                    items = data['results']
                    print(f"   Получено (с пагинацией): {len(items)}")
                elif isinstance(data, list):
                    items = data
                    print(f"   Получено (список): {len(items)}")
                else:
                    items = []
                    print(f"   Неожиданный формат: {data}")

                if not items:
                    return f"❌ {endpoint} не найдено."

                result = f"✅ Найдено {len(items)} {endpoint}"
                if ordering:
                    # Красиво форматируем название сортировки
                    order_desc = {
                        '-nominal_range': 'по мощности (от максимальной)',
                        '-max_efficiency': 'по КПД (от максимального)',
                        '-nominal_head': 'по напору (от максимального)',
                        '-depth': 'по глубине (от максимальной)',
                        '-nominal_power': 'по мощности (от максимальной)',
                        '-efficiency': 'по КПД (от максимального)',
                    }.get(ordering, f"(сортировка: {ordering})")
                    result += f" {order_desc}"
                result += ":\n\n"

                for i, item in enumerate(items[:limit], 1):
                    result += f"{i}. "
                    if display_fields:
                        # Берем первое поле как название
                        name_field = display_fields[0]
                        name_value = item.get(name_field, '?')
                        result += f"**{name_value}**"

                        # Добавляем остальные поля
                        for field in display_fields[1:]:
                            if field in item:
                                value = item[field]
                                # Красивое форматирование
                                if field == 'nominal_range':
                                    result += f", Q={value} м³/сут"
                                elif field == 'nominal_head_display':
                                    result += f", H={value}"
                                elif field == 'max_efficiency_display':
                                    result += f", КПД={value}"
                                elif field == 'nominal_power':
                                    result += f", {value} кВт"
                                elif field == 'efficiency':
                                    result += f", КПД={value}%"
                                elif field == 'depth':
                                    result += f", глубина={value}"
                                elif field == 'formation_debit':
                                    result += f", дебит={value}"
                                elif field == 'nominal_voltage':
                                    result += f", {value} В"
                                else:
                                    result += f", {field}={value}"
                    result += "\n"

                if len(items) > limit:
                    result += f"\n... и еще {len(items) - limit}"

                print(f"   Возвращаю результат длиной {len(result)} символов")
                return result
            else:
                print(f"   Ошибка ответа: {response.status_code}")
                return f"❌ Ошибка при получении {endpoint}: {response.status_code}"

        except Exception as e:
            print(f"   Исключение: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"❌ Ошибка: {str(e)}"


# ==================== ОСНОВНОЙ ЦИКЛ ====================

if __name__ == "__main__":
    # Создаем ассистента
    assistant = RoboWellAssistant()

    print("=" * 60)
    print("🤖 RoboWell Assistant v3.0 - Полная версия с веб-поиском")
    print("=" * 60)
    print("Я помогу с любыми вопросами по системе:")
    print("📌 Скважины: список, детали, статистика")
    print("📌 Насосы: подбор, характеристики, расчеты")
    print("📌 Двигатели: подбор, тех. анализ, статистика")
    print("📌 Комплексный подбор: оборудование для скважины")
    print("📌 Поиск в интернете: ГОСТы, документация, термины")
    print("\nПримеры запросов:")
    print("  • Покажи список скважин")
    print("  • Подбери насос с подачей 200 м³/сут и напором 500 м")
    print("  • Подбери двигатель к насосу ТД1750-200")
    print("  • Найди габариты двигателя НЭДТ1 22-117 М5Э")
    print("  • Что такое КПД и как его считают?")
    print("  • Расскажи про центробежные насосы")
    print("\n(напиши 'выход' для выхода)")
    print("-" * 60)

    while True:
        try:
            question = input("\n👤 Ваш вопрос: ").strip()

            if not question:
                continue

            if question.lower() in ['выход', 'exit', 'quit', 'q']:
                print("👋 До свидания!")
                break

            print("🤖 Думаю...")
            answer = assistant.ask(question)
            print(f"\n🤖 Ассистент: {answer}")

        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}")