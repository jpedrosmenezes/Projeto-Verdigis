from django.urls import path
from django.contrib.auth import views as auth_views
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
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]