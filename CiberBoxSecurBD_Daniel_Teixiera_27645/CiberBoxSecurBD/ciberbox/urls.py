from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/novo/', views.cliente_criar, name='cliente_criar'),
    path('clientes/<int:cliente_id>/', views.cliente_detalhe, name='cliente_detalhe'),
    path('clientes/<int:cliente_id>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<int:cliente_id>/estado/', views.cliente_alterar_estado, name='cliente_alterar_estado'),
    path('clientes/<int:cliente_id>/contactos/novo/', views.contacto_criar, name='contacto_criar'),
    path('contactos/<int:contacto_id>/eliminar/', views.contacto_eliminar, name='contacto_eliminar'),

    path('utilizadores/', views.utilizadores_lista, name='utilizadores_lista'),
    path('utilizadores/novo/', views.utilizador_criar, name='utilizador_criar'),
    path('utilizadores/<int:utilizador_id>/editar/', views.utilizador_editar, name='utilizador_editar'),
    path('utilizadores/<int:utilizador_id>/estado/', views.utilizador_alterar_estado, name='utilizador_alterar_estado'),

    path('ativos/', views.ativos_lista, name='ativos_lista'),
    path('ativos/novo/', views.ativo_criar, name='ativo_criar'),
    path('ativos/<int:ativo_id>/editar/', views.ativo_editar, name='ativo_editar'),
    path('ativos/<int:ativo_id>/eliminar/', views.ativo_eliminar, name='ativo_eliminar'),

    path('incidentes/', views.incidentes_lista, name='incidentes_lista'),
    path('incidentes/novo/', views.incidente_criar, name='incidente_criar'),
    path('incidentes/<int:incidente_id>/editar/', views.incidente_editar, name='incidente_editar'),
    path('incidentes/<int:incidente_id>/eliminar/', views.incidente_eliminar, name='incidente_eliminar'),

    path('avaliacoes/', views.avaliacoes_lista, name='avaliacoes_lista'),
    path('avaliacoes/nova/', views.avaliacao_criar, name='avaliacao_criar'),
    path('avaliacoes/<int:avaliacao_id>/eliminar/', views.avaliacao_eliminar, name='avaliacao_eliminar'),

    path('documentos/', views.documentos_lista, name='documentos_lista'),
    path('documentos/novo/', views.documento_criar, name='documento_criar'),
    path('documentos/<int:documento_id>/download/', views.documento_download, name='documento_download'),
    path('documentos/<int:documento_id>/eliminar/', views.documento_eliminar, name='documento_eliminar'),

    path('pedidos/', views.pedidos_lista, name='pedidos_lista'),
    path('pedidos/novo/', views.pedido_criar, name='pedido_criar'),
    path('pedidos/<int:pedido_id>/', views.pedido_detalhe, name='pedido_detalhe'),
    path('pedidos/<int:pedido_id>/estado/', views.pedido_alterar_estado, name='pedido_alterar_estado'),

    path('importacoes/', views.importacao_excel, name='importacao_excel'),
    path('importacoes/preview/<str:token>/', views.importacao_preview, name='importacao_preview'),
    path('importacoes/preview/<str:token>/confirmar/', views.importacao_confirmar, name='importacao_confirmar'),
    path('importacoes/<int:importacao_id>/', views.importacao_relatorio, name='importacao_relatorio'),

    path('logs/', views.logs_lista, name='logs_lista'),
]
