from django.urls import path
from . import views_web


urlpatterns = [
    path('', views_web.dashboard, name='dashboard'),
    path('wells/', views_web.well_list, name='well_list'),
    path('wells/<int:pk>/', views_web.well_detail, name='well_detail'),
    path('pumps/', views_web.pump_list, name='pump_list'),
    path('pumps/<int:pk>/', views_web.pump_detail, name='pump_detail'),
    path('motors/', views_web.motor_list, name='motor_list'),
    path('motors/<int:pk>/', views_web.motor_detail, name='motor_detail'),
    path('pump-chart/<int:pk>/', views_web.pump_chart_data, name='pump_chart_data'),
    path('motor-chart/<int:pk>/', views_web.motor_chart_data, name='motor_chart_data'),
    path('wells/<int:pk>/telemetry/', views_web.well_telemetry, name='well_telemetry'),
    path('wells/<int:pk>/telemetry-chart/', views_web.telemetry_chart_data, name='telemetry_chart'),
    path('wells/<int:pk>/dashboard/', views_web.well_dashboard, name='well_dashboard'),
    # path('alerts/', views_web.alert_list, name='alert_list'),
    path('commands/', views_web.command_logs, name='command_logs'),
    path('equipment_select/', views_web.equipment_select, name='equipment_select'),
]
