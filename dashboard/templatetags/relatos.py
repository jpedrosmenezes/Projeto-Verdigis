from django import template

from dashboard.services import nome_exibido as _nome_exibido

register = template.Library()


@register.simple_tag(takes_context=True)
def nome_exibido(context, relato):
    """Nome do autor como cada papel pode ver (ver dashboard.services.nome_exibido)."""
    return _nome_exibido(relato, context['request'])
