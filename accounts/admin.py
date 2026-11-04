from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Company, ConcessaoConsultor, Niche, Notificacao, PerfilConsultor,
    PerfilFuncionario, SolicitacaoVinculo, User, Vinculo,
)

# O admin fica só para depuração: nenhum fluxo do produto depende dele.


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'nome', 'papel', 'is_staff', 'date_joined')
    list_filter = ('papel', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'nome')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados pessoais', {'fields': ('nome', 'telefone', 'bio', 'foto_perfil', 'papel')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'nome', 'password1', 'password2')}),
    )


@admin.register(Niche)
class NicheAdmin(admin.ModelAdmin):
    list_display = ('nome',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'codigo', 'cnpj', 'niche', 'uf', 'responsavel', 'created_at')
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj', 'codigo')
    list_filter = ('niche', 'uf')
    readonly_fields = ('codigo',)


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'tipo', 'cargo', 'setor', 'criado_em')
    list_filter = ('tipo', 'company')


@admin.register(SolicitacaoVinculo)
class SolicitacaoVinculoAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'company', 'status', 'criada_em')
    list_filter = ('status',)


admin.site.register(PerfilFuncionario)
admin.site.register(PerfilConsultor)
admin.site.register(ConcessaoConsultor)
admin.site.register(Notificacao)
