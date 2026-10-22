import re

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator
from django.db import models
from django.templatetags.static import static

from .validators import validate_cnpj, validate_cpf


class UserProfile(models.Model):
    TIPO_CHOICES = [
        ('FUNCIONARIO', 'Funcionário'),
        ('EMPRESA', 'Empresa'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default='FUNCIONARIO')
    nome_empresa = models.CharField(max_length=150, blank=True)
    nome = models.CharField(max_length=150, blank=True)
    cnpj = models.CharField(max_length=18, blank=True)
    email = models.EmailField(blank=True)
    foto_perfil = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    cpf = models.CharField(max_length=11, blank=True, validators=[validate_cpf])
    telefone = models.CharField(max_length=11, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cpf'],
                condition=~models.Q(cpf=''),
                name='accounts_userprofile_cpf_unico',
            ),
        ]

    @property
    def avatar_url(self):
        if self.foto_perfil:
            return self.foto_perfil.url
        return static('img/default-avatar.png')

    def __str__(self):
        return f"Perfil de {self.user.username}"


class Niche(models.Model):
    nome = models.CharField("Nicho", max_length=100, unique=True)
    description = models.TextField("Orientações", blank=True)

    def __str__(self):
        return self.nome


class Company(models.Model):
    razao_social = models.CharField("Razão Social", max_length=255)
    nome_fantasia = models.CharField("Nome Fantasia", max_length=255)
    cnpj = models.CharField("CNPJ", max_length=18, unique=True, validators=[validate_cnpj])
    inscricao_estadual = models.CharField("Inscrição Estadual", max_length=20, blank=True)
    inscricao_municipal = models.CharField("Inscrição Municipal", max_length=20, blank=True)
    niche = models.ForeignKey(Niche, on_delete=models.PROTECT, verbose_name="Nicho")

    cep = models.CharField("CEP", max_length=9)
    logradouro = models.CharField("Logradouro", max_length=255)
    numero = models.CharField("Número", max_length=10)
    complemento = models.CharField("Complemento", max_length=100, blank=True)
    bairro = models.CharField("Bairro", max_length=100)
    cidade = models.CharField("Cidade", max_length=100)
    uf = models.CharField("UF", max_length=2)

    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="companies",
        verbose_name="Responsável",
    )

    email_corporativo = models.EmailField("E-mail corporativo")
    telefone_fixo = models.CharField(
        "Telefone fixo", max_length=15,
        validators=[RegexValidator(r"^\(?\d{2}\)?\s?\d{4}-?\d{4}$", "Telefone inválido.")],
    )
    celular_whatsapp = models.CharField(
        "Celular/WhatsApp", max_length=15,
        validators=[RegexValidator(r"^\(?\d{2}\)?\s?9\d{4}-?\d{4}$", "Celular inválido.")],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    senha_acesso = models.CharField(
        "Senha de acesso dos funcionários", max_length=128, blank=True, editable=False
    )

    def set_senha_acesso(self, raw):
        self.senha_acesso = make_password(raw)

    def check_senha_acesso(self, raw):
        return bool(self.senha_acesso) and check_password(raw, self.senha_acesso)

    def save(self, *args, **kwargs):
        self.cnpj = re.sub(r"[^0-9A-Za-z]", "", self.cnpj).upper()
        self.cep = re.sub(r"\D", "", self.cep)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_fantasia


class Funcionario(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="FUNCIONARIO"
    )
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="FUNCIONARIO")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.company})"