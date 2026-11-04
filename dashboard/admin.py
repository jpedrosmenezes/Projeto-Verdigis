from django.contrib import admin

from .models import (
    InteresseParceria, Meta, PerfilParceria, QualidadeESG, RecursoAcessibilidade, RelatoSocialVerdigis,
)


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'company', 'tipo', 'pilar_esg', 'prioridade', 'deadline', 'completo')
    list_filter = ('pilar_esg', 'prioridade', 'completo', 'tipo')
    search_fields = ('nome', 'resumo')


@admin.register(RelatoSocialVerdigis)
class RelatoSocialVerdigisAdmin(admin.ModelAdmin):
    list_display = ('tema_esg', 'sentimento', 'company', 'eh_anonimo', 'data_registro')
    list_filter = ('tema_esg', 'sentimento', 'eh_anonimo')
    search_fields = ('mensagem',)
    date_hierarchy = 'data_registro'
    # O autor nunca aparece, nem aqui: o anonimato vale em todas as telas.
    exclude = ('usuario',)

@admin.register(QualidadeESG)
class QualidadeESGAdmin(admin.ModelAdmin):
    list_display = ('nome', 'pilar')
    list_filter = ('pilar',)
    search_fields = ('nome',)


@admin.register(RecursoAcessibilidade)
class RecursoAcessibilidadeAdmin(admin.ModelAdmin):
    search_fields = ('nome',)


@admin.register(PerfilParceria)
class PerfilParceriaAdmin(admin.ModelAdmin):
    list_display = ('company', 'visivel', 'atualizado_em')
    list_filter = ('visivel',)
    filter_horizontal = ('qualidades', 'acessibilidades', 'necessidades')


@admin.register(InteresseParceria)
class InteresseParceriaAdmin(admin.ModelAdmin):
    list_display = ('origem', 'destino', 'pilar', 'criado_em')
    list_filter = ('pilar',)
    date_hierarchy = 'criado_em'