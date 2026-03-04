from celery import shared_task
from core.services.telemetry_api import TelemetryAPIClient
from core.models import Well


@shared_task
def fetch_well_telemetry(well_id):
    """
    Асинхронное получение телеметрии для одной скважины.
    """
    print(f"Запуск задачи для скважины {well_id}")
    client = TelemetryAPIClient()
    result = client.fetch_well_telemetry(well_id)
    return {
        'well_id': well_id,
        'success': result,
        'status': 'completed'
    }


@shared_task
def fetch_all_telemetry():
    """
    Получение телеметрии для всех скважин.
    """
    print("Запуск получения данных для всех скважин")
    client = TelemetryAPIClient()
    results = {'success': [], 'failed': []}

    for well in Well.objects.all():
        result = client.fetch_well_telemetry(well.id)
        if result:
            results['success'].append(well.id)
        else:
            results['failed'].append(well.id)

    return results