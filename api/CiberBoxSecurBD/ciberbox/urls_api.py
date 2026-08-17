from django.urls import path
from . import api

urlpatterns = [
    path('csrf/', api.csrf_view, name='api_csrf'),
    path('login/', api.login_api, name='api_login'),
    path('logout/', api.logout_api, name='api_logout'),
    path('me/', api.me_api, name='api_me'),
    path('dashboard/', api.dashboard_api, name='api_dashboard'),
    path('clientes/', api.clientes_api, name='api_clientes'),
    path('clientes/<int:id>/', api.cliente_detalhe_api, name='api_cliente_detalhe'),
    path('utilizadores/', api.utilizadores_api, name='api_utilizadores'),
    path('ativos/', api.ativos_api, name='api_ativos'),
    path('incidentes/', api.incidentes_api, name='api_incidentes'),
    path('documentos/', api.documentos_api, name='api_documentos'),
    path('pedidos/', api.pedidos_api, name='api_pedidos'),
    path('avaliacoes/', api.avaliacoes_api, name='api_avaliacoes'),
    path('logs/', api.logs_api, name='api_logs'),
    path('opcoes/', api.opcoes_api, name='api_opcoes'),
]
