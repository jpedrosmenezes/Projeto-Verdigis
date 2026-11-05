from django.urls import path
from . import views, views_parcerias

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='dashboard'),
    path('contexto/', views.trocar_contexto, name='contexto'),

    # Equipe: solicitações, funcionários e consultores
    path('equipe/', views.equipe, name='equipe'),
    path('equipe/solicitacoes/<int:solicitacao_id>/', views.responder_solicitacao, name='responder_solicitacao'),
    path('equipe/membros/<int:vinculo_id>/remover/', views.remover_membro, name='remover_membro'),
    path('equipe/consultores/<int:vinculo_id>/permissoes/', views.salvar_capacidades, name='salvar_capacidades'),

    # Fábrica de metas
    path('metas/', views.fabrica_metas_view, name='fabrica_metas'),
    path('metas/<int:meta_id>/editar/', views.editar_meta_view, name='editar_meta'),
    path('metas/<int:meta_id>/concluir/', views.alternar_conclusao_view, name='alternar_conclusao'),
    path('metas/<int:meta_id>/deletar/', views.deletar_meta_view, name='deletar_meta'),

    # Relatos (Central de Avaliações)
    path('avaliacao/', views.dashboard_social_verdigis, name='dashboard_social'),
    path('avaliacao/nova/', views.adicionar_avaliacao, name='adicionar_avaliacao'),
    path('avaliacao/meus/', views.meus_relatos, name='meus_relatos'),
    path('avaliacao/<int:relato_id>/', views.detalhe_relato_view, name='detalhe_relato'),
    path('avaliacao/<int:relato_id>/ocultar/', views.ocultar_relato_view, name='ocultar_relato'),
    path('avaliacao/<int:relato_id>/restaurar/', views.restaurar_relato_view, name='restaurar_relato'),
    
    # Painel de Parcerias
    path('parcerias/', views_parcerias.painel, name='parcerias'),
    path('parcerias/eixo/<str:pilar>/', views_parcerias.eixo, name='parcerias_eixo'),
    path('parcerias/empresa/<int:company_id>/', views_parcerias.detalhe, name='parcerias_detalhe'),
    path('parcerias/empresa/<int:company_id>/match/', views_parcerias.alternar_match, name='parcerias_match'),
    path('parcerias/matches/', views_parcerias.meus_matches, name='parcerias_matches'),
    path('parcerias/perfil/', views_parcerias.meu_perfil, name='parcerias_perfil'),

    # Encerrar a conta da empresa
    path('empresa/apagar/', views.apagar_empresa, name='apagar_empresa'),

    # tabela de atividades
    path('visualizar_tabela/', views.visulizar_tabela, name='visulizar_tabela'),
    path('metas/<int:meta_id>/atividades/', views.preencher_tabela, name='preencher_tabela'),
    path('atividades/nova/', views.criar_atividade, name='criar_atividade'),
    path('atividades/<int:atividade_id>/mover/', views.mover_atividade, name='mover_atividade'),

]
