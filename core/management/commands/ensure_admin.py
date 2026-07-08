import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Создаёт суперпользователя, если его нет'

    def handle(self, *args, **options):
        if not User.objects.filter(is_superuser=True).exists():
            password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            User.objects.create_superuser(
                username='admin',
                email='oleg309@yandex.ru',
                password=password,
                is_active=True
            )
            self.stdout.write(self.style.SUCCESS('✅ Суперпользователь создан'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Суперпользователь уже существует'))