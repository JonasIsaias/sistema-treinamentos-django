from django.contrib import admin
from django.urls import include, path
from . import views
from .views import relatorio_por_colaborador

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/frequencia/', views.dashboard_frequencia, name='dashboard_frequencia'),
    path('dashboard/exportar-excel/', views.exportar_dashboard_excel, name='exportar_dashboard_excel'),
    path('dashboard/exportar-pdf/', views.exportar_dashboard_pdf, name='exportar_dashboard_pdf'),

    # Treinamentos
    path('treinamentos/', views.treinamento_list, name='treinamento_list'),
    path('treinamento/<int:treinamento_id>/', views.treinamento_detail, name='treinamento_detail'),
    path('treinamento/novo/', views.treinamento_create, name='treinamento_create'),
    path('treinamento/<int:treinamento_id>/frequencia/', views.registrar_frequencia, name='registrar_frequencia'),

    # Ajax / utilitários
    path('atualizar-colaboradores/', views.atualizar_colaboradores_por_matriculas, name='atualizar_colaboradores'),
]