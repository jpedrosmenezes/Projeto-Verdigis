from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('senha/', views.TrocarSenhaView.as_view(), name='password_change'),
    path('delete/', views.delete, name='delete'),

    path('onboarding/', views.onboarding, name='onboarding'),
    path('onboarding/<str:papel>/', views.onboarding_papel, name='onboarding_papel'),
    path('cep/<str:cep>/', views.buscar_cep, name='buscar_cep'),

    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),

    path('empresas/entrar/', views.entrar_empresa, name='entrar_empresa'),
    path('vinculos/', views.meus_vinculos, name='meus_vinculos'),
    path('vinculos/<int:vinculo_id>/sair/', views.sair_empresa, name='sair_empresa'),
    path('solicitacoes/<int:solicitacao_id>/cancelar/', views.cancelar_solicitacao, name='cancelar_solicitacao'),

    path('notificacoes/', views.notificacoes, name='notificacoes'),
    path('notificacoes/<int:notificacao_id>/', views.abrir_notificacao, name='abrir_notificacao'),
    path('notificacoes/marcar-todas/', views.marcar_todas_lidas, name='marcar_todas_lidas'),
]
