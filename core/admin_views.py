import os
import json
from django.http import FileResponse, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.core.management import call_command

BACKUP_DIR = '/app/backups'


@staff_member_required
def backup_list(request):
    """Список бэкапов"""
    files = []
    if os.path.exists(BACKUP_DIR):
        for f in os.listdir(BACKUP_DIR):
            if f.endswith('.json'):
                path = os.path.join(BACKUP_DIR, f)
                files.append({
                    'name': f,
                    'size': os.path.getsize(path),
                    'modified': os.path.getmtime(path)
                })
    files = sorted(files, key=lambda x: x['modified'], reverse=True)
    return render(request, 'admin/backup_list.html', {'files': files})


@staff_member_required
def backup_download(request):
    """Скачать бэкап"""
    filename = request.GET.get('file')
    if not filename:
        messages.error(request, 'Файл не указан')
        return redirect('backup_list')

    file_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(file_path):
        messages.error(request, 'Файл не найден')
        return redirect('backup_list')

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)


@staff_member_required
def backup_create(request):
    """Создать новый бэкап"""
    import datetime
    os.makedirs(BACKUP_DIR, exist_ok=True)
    filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    file_path = os.path.join(BACKUP_DIR, filename)

    call_command('dumpdata', '--indent', '2', '--output', file_path)

    messages.success(request, f'Бэкап создан: {filename}')
    return redirect('backup_list')


@staff_member_required
def backup_restore(request):
    """Восстановить из бэкапа"""
    if request.method == 'POST':
        filename = request.POST.get('file')
        if not filename:
            messages.error(request, 'Файл не указан')
            return redirect('backup_list')

        file_path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(file_path):
            messages.error(request, 'Файл не найден')
            return redirect('backup_list')

        # Очищаем старые данные и загружаем новые
        call_command('flush', '--noinput')
        call_command('loaddata', file_path)

        messages.success(request, f'Бэкап {filename} восстановлен!')
        return redirect('backup_list')

    return JsonResponse({'error': 'Метод не разрешён'}, status=405)
