from django.contrib import admin

from .models import Company, Funcionario, Niche, UserProfile


@admin.register(Niche)
class NicheAdmin(admin.ModelAdmin):
    list_display = ('nome',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'razao_social', 'cnpj', 'niche', 'responsavel', 'created_at')
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj')
    list_filter = ('niche', 'uf')


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'created_at')
    list_filter = ('company',)


admin.site.register(UserProfile)