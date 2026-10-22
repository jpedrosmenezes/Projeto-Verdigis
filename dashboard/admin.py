from django.contrib import admin

# Register your models here.
from .models import Meta, RelatoSocialVerdigis


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario', 'pilar_esg', 'prioridade', 'deadline', 'completo')
    list_filter = ('pilar_esg', 'prioridade', 'completo')
    search_fields = ('nome', 'resumo', 'usuario__username')


@admin.register(RelatoSocialVerdigis)
class RelatoSocialVerdigisAdmin(admin.ModelAdmin):
    list_display = ('tema_esg', 'sentimento', 'eh_anonimo', 'data_registro')
    list_filter = ('tema_esg', 'sentimento', 'eh_anonimo')
    search_fields = ('mensagem',)
    date_hierarchy = 'data_registro'
