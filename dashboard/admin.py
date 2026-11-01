from django.contrib import admin

from .models import Meta, RelatoSocialVerdigis


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
