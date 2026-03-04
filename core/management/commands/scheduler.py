from django.core.management.base import BaseCommand
from core.scheduler import scheduler
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Управление планировщиком задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['start', 'stop', 'restart', 'status', 'jobs'],
            default='status',
            help='Действие с планировщиком'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'start':
            scheduler.start()
            self.stdout.write(self.style.SUCCESS("Планировщик запущен"))

        elif action == 'stop':
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS("Планировщик остановлен"))

        elif action == 'restart':
            scheduler.shutdown()
            scheduler.start()
            self.stdout.write(self.style.SUCCESS("Планировщик перезапущен"))

        elif action == 'status':
            if scheduler.scheduler.running:
                self.stdout.write(self.style.SUCCESS("Планировщик работает"))
            else:
                self.stdout.write(self.style.WARNING("Планировщик остановлен"))

        elif action == 'jobs':
            jobs = scheduler.get_jobs()
            if jobs:
                self.stdout.write("Активные задачи:")
                for job in jobs:
                    self.stdout.write(f"  - {job.name} (id: {job.id})")
                    self.stdout.write(f"    Следующий запуск: {job.next_run_time}")
            else:
                self.stdout.write("Нет активных задач")