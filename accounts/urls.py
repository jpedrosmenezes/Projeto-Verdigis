from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('delete/', views.delete, name='delete'),
    path('profile/', views.profile, name='profile'),
    path('company/register/', views.company_register, name='company_register'),
    path('company/success/', views.company_success, name='company_success'),
    path('cep/<str:cep>/', views.buscar_cep, name='buscar_cep'),
    path('signup/funcionario/', views.signup_funcionario, name='signup_funcionario'),
    path('login/funcionario/', views.login_funcionario, name='login_funcionario'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
]