from django import template

from accounts.permissions import pode as _pode

register = template.Library()


@register.simple_tag(takes_context=True)
def pode(context, acao, obj=None):
    """Uso: {% pode 'meta.criar' as pode_criar %} ou {% pode 'meta.editar' meta as pode_editar %}."""
    request = context.get('request')
    if request is None or not request.user.is_authenticated:
        return False
    return _pode(request, acao, obj)
