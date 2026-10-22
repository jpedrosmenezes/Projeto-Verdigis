import re
from django.core.exceptions import ValidationError


def validate_cnpj(value):
    cnpj = re.sub(r"[^0-9A-Za-z]", "", value or "").upper()
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj) or cnpj == cnpj[0] * 14:
        raise ValidationError("CNPJ inválido.")

    def dv(base):
        pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2][-len(base):]
        resto = sum((ord(c) - 48) * p for c, p in zip(base, pesos)) % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = dv(cnpj[:12])
    d2 = dv(cnpj[:12] + d1)
    if cnpj[12:] != d1 + d2:
        raise ValidationError("CNPJ inválido.")


def validate_cpf(value):
    cpf = re.sub(r"\D", "", value or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    def dv(base):
        soma = sum(int(d) * p for d, p in zip(base, range(len(base) + 1, 1, -1)))
        return str((soma * 10) % 11 % 10)

    d1 = dv(cpf[:9])
    d2 = dv(cpf[:9] + d1)
    if cpf[9:] != d1 + d2:
        raise ValidationError("CPF inválido.")