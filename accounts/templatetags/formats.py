import re

from django import template

register = template.Library()


@register.filter
def telefone_br(valor):
    """81997834568 -> (81) 99783-4568 | 8133334444 -> (81) 3333-4444"""
    digitos = re.sub(r'\D', '', str(valor or ''))
    if len(digitos) == 11:
        return f'({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}'
    if len(digitos) == 10:
        return f'({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}'
    return valor or ''