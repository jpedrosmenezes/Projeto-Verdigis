from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Página inicial do dashboard
    path('', views.home, name='dashboard'),
    
    #listar e criar metas
    path('metas/', views.fabrica_metas_view, name='fabrica_metas'),
    
    #editar uma meta
    path('metas/<int:meta_id>/editar/', views.editar_meta_view, name='editar_meta'),
    
    # Rota para alternar a conclusão de uma meta
    path('metas/<int:meta_id>/concluir/', views.alternar_conclusao_view, name='alternar_conclusao'),
    
    # Rota para deletar uma meta
    path('metas/<int:meta_id>/deletar/', views.deletar_meta_view, name='deletar_meta'),

    # Rota para avaliações
    path('avaliacao/', views.dashboard_social_verdigis, name='dashboard_social'),

    path('avaliacao/<int:relato_id>/', views.detalhe_relato_view, name='detalhe_relato'),
    
    path('avaliacao/nova/', views.adicionar_avaliacao, name='adicionar_avaliacao'),

        # Lista de funcionários da empresa (só o responsável)
    path('funcionarios/', views.funcionarios_view, name='funcionarios'),
]
