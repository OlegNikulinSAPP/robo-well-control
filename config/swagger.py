from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title='RoboWell Control System API',
        default_version='vq',
        description='API для управления добывающими скважинами с ЭЦН',
        terms_of_service='https://',
        contact=openapi.Contact(email='nikulinov@sistemaservis.ru'),
        license=openapi.License(name='BSD License'),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)
