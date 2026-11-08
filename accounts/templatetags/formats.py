import re

from django import template

register = template.Library()


def _digitos(valor):
    return re.sub(r'\D', '', str(valor or ''))


@register.filter
def telefone_br(valor):
    """81997834568 -> (81) 99783-4568 | 8133334444 -> (81) 3333-4444"""
    digitos = _digitos(valor)
    if len(digitos) == 11:
        return f'({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}'
    if len(digitos) == 10:
        return f'({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}'
    return valor or ''


@register.filter
def cpf_br(valor):
    """12345678901 -> 123.456.789-01"""
    d = _digitos(valor)
    if len(d) != 11:
        return valor or ''
    return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}'


@register.filter
def cnpj_br(valor):
    """12345678000190 -> 12.345.678/0001-90 (aceita o CNPJ alfanumérico)."""
    v = re.sub(r'[^0-9A-Za-z]', '', str(valor or '')).upper()
    if len(v) != 14:
        return valor or ''
    return f'{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}'
